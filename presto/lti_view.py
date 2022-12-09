"""
Software developed by Pieter W.G. Bots for the PrESTO project
Code repository: https://github.com/pwgbots/presto
Project wiki: http://presto.tudelft.nl/wiki

Copyright (c) 2022 Delft University of Technology

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the
Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .models import Course, CourseEstafette, CourseStudent, Profile, Role

# python modules
from datetime import timedelta
from hashlib import md5
import logging
from pylti.common import (
    LTIException,
    LTINotInSessionException,
    LTIPostMessageException,
    LTI_PROPERTY_LIST,
    LTIRoleException,
    LTI_ROLES,
    LTI_SESSION_KEY,
    post_message,
    verify_request_common
)
from re import match, sub
import time
from urllib.parse import unquote_plus
from xml.etree import ElementTree as etree

# presto modules
from presto.generic import generic_context, inform_user, warn_user
from presto.student import student
from presto.utils import log_message

# As edX users need not specify their mail address, their user email is set to
# a default value.
# TO DO: Let users change this field (once) via the awards page.
EDX_DEFAULT_MAIL_ADDRESS = 'someone@mooc.edx'

# Let pylti error messages be printed to standard output.
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)
logging.getLogger('pylti.common').addHandler(logging.StreamHandler())


# LTI needs a dict with consumer IDs as keys and for each key a dict
# {secret: code} as value.
LTI_CONSUMERS = {}

# NOTE: edX LTI request has two additional attributes.
LTI_PROPERTY_LIST_EX = ['context_title', 'custom_component_display_name']

# NOTE: In production, this flag should be set to True.
LTI_VERIFICATION = False

# NOTE: Since edX terms and conditions prohibit storing its user IDs in
#       a database, these IDs are hashed using the function and parameters
#       defined below.
#       This means that registered edX users will no longer be recognized
#       if the hash function or its multiplier parameter are modified!!

# returns a deterministic hash of a given string
def n_hash(string, multiplier=1):
    return md5(((settings.SECRET_KEY + string) * multiplier
        ).encode('ascii', 'ignore')).hexdigest()

# n_hash multipliers used for security of edX user registration.
FORM_MULTIPLIER = 11
DB_MULTIPLIER = 37
PWD_MULTIPLIER = 19


@method_decorator(csrf_exempt, name='dispatch')
# No login required for LTI link.
def lti_view(request, **kwargs):
    # Initialize the LTI consumer list.
    global LTI_CONSUMERS

    # NOTE: As each course estafette is assumed to be a specific assignment
    #       in edX, the edX course designer/manager must have a unique
    #       consumer ID and associated secret for that assignment.
    for ce in CourseEstafette.objects.filter(course__is_edX=True):
        cs_tuple = ce.LTI_consumer_secret()
        LTI_CONSUMERS[cs_tuple[0]] = {'secret': cs_tuple[1]}

    # Create an LTI object that accepts any request type and any role type.
    lti = LTI('any', 'any')
    log_message('LTI user ID: ' + lti.user_id(request))
    # Verify the LTI consumer request.
    try:
        lti.verify(request)
    except LTIException:
        log_message('LTI EXCEPTION!')
        lti.clear_session(request)

    log_message('Verified LTI user ID:' + lti.user_id(request))

    post_data = lti._params(request)
    context = generic_context(request)

    # simple test to see whether POST data comes from edX
    if post_data.get('user_id', ''):
        uid = post_data.get('user_id', '')
        c_code = (unquote_plus(post_data.get('context_id', '')) + ':').split(':')[1]
    else:
        c_code = post_data.get('course', '')
    # check whether the specified course exists
    qset = Course.objects.filter(code=c_code)
    if not qset:
        context['error'] = 'Unknown course code "{}"'.format(c_code)
        log_message(context['error'])
        return render(request, 'presto/error.html', context)
    # get the course instance -- will be used further below
    presto_course = qset.first()

    # check whether a grade needs to be passed back
    extra = kwargs.get('extra', '')
    if extra == 'grade':
        return post_grade(request, 0.234)

    # check whether a new user is registering
    if extra == 'register':
        uid = post_data.get('uid', '')
        # validate user ID against its hash
        if not uid or post_data.get('hash', '') != n_hash(uid, FORM_MULTIPLIER):
            context['error'] = 'Security alert: registration form integrity has been compromised'
            log_message(context['error'])
            return render(request, 'presto/error.html', context)

        # check if names comply with restrictions
        f_name = sub('\s+', ' ', post_data.get('first', '')).strip()
        l_name = sub('\s+', ' ', post_data.get('last', '')).strip()
        if not match('^[a-zA-Z][a-zA-Z0-9\s\.\-\'\(\)]{5,48}$', f_name + l_name):
            warn_user(
                context,
                'Invalid name or alias',
                'Your name or alias "{} {}" does not comply with the stated restrictions.'.format(
                    f_name, l_name
                    )
                )
        else:
            # check if name combination is already in use
            qset = User.objects.filter(first_name__iexact=f_name, last_name__iexact=l_name)
            if qset:
                warn_user(
                    context,
                    'Name or alias already in use',
                    """Some other user has registered under this name.
                       Please try again with a (slightly) different name."""
                    )
            else:
                # Register new user under specified names in the database.
                # NOTE: The "ZZZ-" prefix serves to move edX users to the
                #       bottom of the user list in the database.
                u_name = 'ZZZ-' + n_hash(uid, DB_MULTIPLIER)
                u = User.objects.create_user(
                    username=u_name,
                    first_name=f_name,
                    last_name=l_name,
                    email=EDX_DEFAULT_MAIL_ADDRESS,
                    password=n_hash(uid, PWD_MULTIPLIER)
                    )
                log_message('Created new edX user: ' + u_name)
                up = Profile.objects.get(user=u)
                up.is_edx_user = True
                up.roles.add(Role.objects.get(name='Student'))
                up.save()

    # use HASHED edX learner ID as Django username
    u_name = 'ZZZ-' + n_hash(uid, DB_MULTIPLIER)

    # check whether the passed user ID has (just now) been registered
    qset = User.objects.filter(username=u_name)
    if qset:
        # log in as this registered user
        presto_user = qset.first()
        presto_user.backend = settings.DEMO_USR_BACKEND
        login(request, presto_user)
        # get new generic context data for this user
        context = generic_context(request)
        # enroll user in this course (if not already)
        if CourseStudent.objects.filter(course=presto_course, user=presto_user).count() == 0:
            cs = CourseStudent(course=presto_course, user=presto_user)
            cs.save()
            log_message(
                'Automatically enrolled in {} (as edX student)'.format(presto_course.code),
                presto_user
                )
        # display the student view
        return student(request)

    # if not, show the registration page
    context['page_title'] = 'Presto registration'
    # pass the user's LTI user ID
    context['uid'] = uid
    # for the sake of security also pass a deterministic hash
    context['hash'] = n_hash(uid, FORM_MULTIPLIER)
    # also pass the course code
    context['course'] = presto_course.code
    return render(request, 'presto/lti_view.html', context)


# posts user grade (float between 0 and 1) to the LTI consumer
def post_grade(request, score=0.123):
    # create an LTI object that accepts any request type and any role type
    lti = LTI('any', 'any')
    if not score:
        try:
            score = float(request.POST.get('score', 0))
        except Exception as e:
            log_message('No LTI grade specified for' + lti.user_fullname(request))
            score = 0

    redirect_url = request.POST.get('next', '/')
    launch_url = request.POST.get('launch_url', None)
    # use time stamp as message identifier
    message_id = '{:.0f}'.format(time.time())
    # create the LTI message
    xml = lti.generate_request_xml(message_id, 'replaceResult', lti.lis_result_sourcedid(request),
        score, launch_url)
    # try to post it
    name = lti.user_fullname(request)
    if post_message(LTI_CONSUMERS, lti.oauth_consumer_key(request),
                    lti.lis_outcome_service_url(request), xml):
        log_message('LTI score ({:.3f} for {}) submitted'.format(score, name))
        # return empty response, as message does not appear
        return HttpResponse(
            'Present score for {} is {:.3f}'.format(name, score),
            content_type='text/plain'
            )
        # return HttpResponseRedirect(redirect_url)
    else:
        log_message(
            'ERROR: Failed to submit LTI score ({:.3f} for {})'.format(score, name))
        raise LTIPostMessageException('Failed to post grade')



# an LTI object represents an abstraction of the current LTI session (if any)
# NOTE: the code below has been adapted from https://github.com/ccnmtl/django-lti-provider
class LTI(object):

    def __init__(self, request_type, role_type):
        self.request_type = request_type
        self.role_type = role_type

    # invalidates the browser session
    def clear_session(self, request):
        request.session.flush()

    # stores all of the LTI parameters into a session dict for use in views
    def initialize_session(self, request, params):
        # standard LTI properties
        for prop in LTI_PROPERTY_LIST:
            if params.get(prop, None):
                request.session[prop] = params[prop]
        # custom LTI properties
        for prop in LTI_PROPERTY_LIST_EX:
            if params.get(prop, None):
                request.session[prop] = params[prop]

    # raises an exception if the LTI request is not valid
    def verify(self, request):
        if self.request_type == 'session':
            self._verify_session(request)
        elif self.request_type == 'initial':
            self._verify_request(request)
        elif self.request_type == 'any':
            self._verify_any(request)
        else:
            raise LTIException('Unknown request type')
        return True

    # gets the request parameters as a plain dict
    def _params(self, request):
        if request.method == 'POST':
            return dict(request.POST.items())
        else:
            return dict(request.GET.items())

    # checks whether the request is a valid LTI  request
    def _verify_any(self, request):
        params = self._params(request)
        if 'oauth_consumer_key' in params:
            # appears to be an initial launch request => full verification
            self._verify_request(request)
        else:
            # just check the session for the LTI_SESSION_KEY
            self._verify_session(request)

    # verifies that session was already created
    @staticmethod
    def _verify_session(request):
        # NOTE: the LTI_SESSION_KEY request parameter is "lti_authenticated"
        if not request.session.get(LTI_SESSION_KEY, False):
            raise LTINotInSessionException('Session expired or unavailable')

    # raises LTIException if request is not valid
    def _verify_request(self, request):
        try:
            params = self._params(request)
            # NOTE: for testing purposes, LTI request verification may be skipped
            if LTI_VERIFICATION:
                verify_request_common(LTI_CONSUMERS, request.build_absolute_uri(),
                    request.method, request.META, params)
            self._validate_role()
            self.clear_session(request)
            self.initialize_session(request, params)
            request.session[LTI_SESSION_KEY] = True
            return True
        except LTIException:
            self.clear_session(request)
            request.session[LTI_SESSION_KEY] = False
            raise

    # raises an exception is user does not have the specified role
    def _validate_role(self):
        # NOTE: the permitted role is specfied when the LTI object is instatiated
        if self.role_type != u'any':
            if self.role_type in LTI_ROLES:
                role_list = LTI_ROLES[self.role_type]
                # find the intersection of the roles
                roles = set(role_list) & set(self.user_roles())
                if len(roles) < 1:
                    raise LTIRoleException('Not authorized')
            else:
                raise LTIException('Unknown role "{}"'.format(self.role_type))
        return True

    def consumer_user_id(self, request):
        return self.oauth_consumer_key(request) + '-' + self.user_id(request)

    def course_context(self, request):
        return request.session.get('context_id', None)

    def course_title(self, request):
        return request.session.get('context_title', None)

    def is_administrator(self, request):
        return 'administrator' in request.session.get('roles', '').lower()

    def is_instructor(self, request):
        roles = request.session.get('roles', '').lower()
        return 'instructor' in roles or 'staff' in roles

    def lis_outcome_service_url(self, request):
        return request.session.get('lis_outcome_service_url', None)

    def lis_result_sourcedid(self, request):
        return request.session.get('lis_result_sourcedid', None)

    def oauth_consumer_key(self, request):
        return request.session.get('oauth_consumer_key', None)

    def user_email(self, request):
        return request.session.get('lis_person_contact_email_primary', None)

    def user_fullname(self, request):
        name = request.session.get('lis_person_name_full', None)
        if not name or len(name) < 1:
            name = self.user_id(request)
        return name or ''

    def user_id(self, request):
        return request.session.get('user_id', None)

    # NOTE: returns the LTI user roles as a list of strings
    def user_roles(self, request):
        roles = request.session.get('roles', None)
        if not roles:
            return []
        return roles.lower().split(',')

    # generates LTI 1.1 XML for posting a result to the LTI consumer
    def generate_request_xml(self, message_identifier_id, operation,
                             lis_result_sourcedid, score, launch_url):
        root = etree.Element('imsx_POXEnvelopeRequest',
            xmlns='http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0')
        header = etree.SubElement(root, 'imsx_POXHeader')
        header_info = etree.SubElement(header, 'imsx_POXRequestHeaderInfo')
        version = etree.SubElement(header_info, 'imsx_version')
        version.text = 'V1.0'
        message_identifier = etree.SubElement(header_info, 'imsx_messageIdentifier')
        message_identifier.text = message_identifier_id
        body = etree.SubElement(root, 'imsx_POXBody')
        xml_request = etree.SubElement(body, operation + 'Request')
        record = etree.SubElement(xml_request, 'resultRecord')
        guid = etree.SubElement(record, 'sourcedGUID')
        sourcedid = etree.SubElement(guid, 'sourcedId')
        sourcedid.text = lis_result_sourcedid
        if score is not None:
            result = etree.SubElement(record, 'result')
            result_score = etree.SubElement(result, 'resultScore')
            language = etree.SubElement(result_score, 'language')
            language.text = 'en'
            text_string = etree.SubElement(result_score, 'textString')
            text_string.text = score.__str__()
            if launch_url:
                result_data = etree.SubElement(result, 'resultData')
                lti_launch_url = etree.SubElement(result_data, 'ltiLaunchUrl')
                lti_launch_url.text = launch_url
        return "<?xml version='1.0' encoding='utf-8'?>\n{}".format(
            etree.tostring(root, encoding='utf-8')) #  .decode('utf-8'))



"""
LTI passes these POST parameters to the called application:
(NOTE: all parameter values are *lists* of strings or numbers)

lti_version: ['LTI-1p0']
lti_message_type: ['basic-lti-launch-request']
launch_presentation_locale: ['en']
launch_presentation_return_url: ['']

lis_person_contact_email_primary: ['email@domain.ext']
lis_result_sourcedid: ['(URL-encoded context id):(resource link id):(user id)']
user_id: [(32 hex digit string)]
roles: ['Student', 'Administrator' and/or 'Instructor']
context_id: [(EdX ID -- course code, name etc. -- of the course calling Presto)]
resource_link_id: [(prefixed 32 hex digit string identifying the specific EdX course assignment for which Presto is called)]

oauth_nonce: [(32 hex digit string)]
oauth_consumer_key: (client key zoals boven besproken, een 8-digit base36 code)
oauth_signature_method: ['HMAC_SHA1']
oauth_version: ['1.0']
oauth_timestamp: [integer value (unix timestamp)]
oauth_signature: [(28 base64 digit string)]
oauth_callback: ['about:blank']

custom_component_display_name: [(the EdX course component name, e.g., "PrESTO (new window)")]

In edge.edx, instructors may define custom parameters.
For Presto to work, these custom parameters must be defined:
(NOTE: the "custom_" prefix is added by EdX, and hence should not be used)

custom_relay: the EdX course relay identifier (five base36 digits) displayed after title (instructors only)

NOTE:
lis_outcome_service_url: ['https://edge.edx.org/courses/course-v1:TUDelft+Sketchdrive+2017/xblock/block-v1:TUDelft+Sketchdrive+2017+type@lti_consumer+block@cf6bd2285495411e8151dbcbbad1d00c/handler_noauth/outcome_service_handler'],


"""

