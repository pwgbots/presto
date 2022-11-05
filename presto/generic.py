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
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone

from .models import NO_SESSION_KEY, Participant, Role, UserSession

# python modules
from datetime import timedelta
from json import dumps, loads
from re import match, sub
import sys
import traceback

# presto modules
from presto.utils import (
    decode,
    encode,
    EXPIRED_SESSION_KEY,
    log_message,
    prefixed_user_name,
    random_hex
    )


BACK_IN_BROWSER = """
You probably went back in your browser, used an old URL, or have opened more
than one Presto window in the same browser.<br>
To prevent this, navigate by only using buttons and menus, and create a plain
bookmark for the Presto website:&nbsp; <tt>{}</tt>
"""

EXPIRED_MSG = """
If this error occurred during regular operations, please
report it to the Presto Administrator.
"""
                
                
# returns user if authenticated; otherwise None
def authenticated_user(request):
    if request.user.is_authenticated:
        return request.user
    else:
        return None


# returns dictionary with context entries relevant for all pages
# NOTE: To test whether the session key needs to be rotated, an encoded key must be passed,
#       or None if this does not apply.
def generic_context(request, test_code=None):
    if settings.PRESTO_URL:
        base_url = settings.PRESTO_URL
    else:
        # assume that "presto" is the root dir to which the index template is directed
        base_url = request.build_absolute_uri().split('/presto/', 1)[0] + '/presto/'

    # get user IP from request
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        settings.USER_IP = x_forwarded_for.split(',')[0]
    else:
        settings.USER_IP = request.META.get('REMOTE_ADDR')

    # start with an empty notification list
    notifications = []
    
    # fetch logged in user
    presto_user = authenticated_user(request)
    user_profile = None
    user_session = None
    user_name = '(unknown user)'
    user_roles = []
    if presto_user:
        # get user specifics
        user_profile = presto_user.profile
        user_name = prefixed_user_name(presto_user)
        
        # get current user roles
        ur_list = user_profile.roles.all().values_list('id', flat=True)

        # ensure that superusers have all roles
        if presto_user.is_superuser:
            for r in Role.objects.exclude(id__in=ur_list):
                user_profile.roles.add(r)
            user_profile.save()

        # ensure that staff (employees) have instructor and developer roles
        if presto_user.is_superuser:
            ur_list = [r.id for r in user_profile.roles.all()]
            for r in Role.objects.filter(name__in=['Instructor', 'Developer']).exclude(id__in=ur_list):
                user_profile.roles.add(r)
            user_profile.save()

        user_roles = user_profile.roles.all()
        
        # CLEANUP: delete all Presto sessions that have been inactive for 24 hours or more
        UserSession.objects.exclude(last_action__gt=timezone.now() - timedelta(days=1)).delete()

        # create a session if none exists yet
        # NOTE: In principle, each user can have only ONE session so as to prevent
        #       all kinds of trouble with repeated uploads, reviews, etc.
        #       However, since demo-users are logged on as the same user,
        #       sessions for these users must be "multiplexed". This is achieved by
        #       registering the Django session key. For regular users, NO_SESSION_KEY
        #       is stored, ensuring that they always get the same session object.
        if presto_user.username == settings.DEMO_USER_NAME:
            # NOTE: if session has just been created, it must be saved before its key is accessible
            if not request.session.session_key:
                request.session.save()
            key = request.session.session_key
        else:
            key = NO_SESSION_KEY
        user_session, created = UserSession.objects.get_or_create(user=presto_user, session_key=key)

        # update the session record, notably the hex keys
        # NOTE: These keys "rotate" each time this "generic context" function is called,
        #       which should be whenever the user moves to a new page.
        #       This "rotation" means that the decoder key gets the value of the former
        #       encoder key, while a new random encoder key is generated.
        #       In this way, these keys are valid only once, and since all database keys
        #       used in GET and POST operations are encoded, the application is secured
        #       against Cross Site Request Forgery.
        #       Hence the Django csrf-protection can remain disabled.
        # NOTE: Keys should not be rotated when a page is refreshed. This can be checked by
        #       first trying to decode with the CURRENT decoder. If that is successful,
        #       no rotation should be done.
        # NOTE: Keys should also NOT be rotated when downloading a file (as this opens a
        #       new tab/window in the browser). The calling routine in download.py signals
        #       this by passing "NOT" as value for the test_code parameter.
        try:
            if test_code != 'NOT':
                # see if decoding succeeds with CURRENT decoder; if yes, keep the current codes
                decode(test_code, user_session.decoder)
        except:
            # if decoding with current decoder fails (possibly because no test_code is passed),
            # then the codes should be rotated
            user_session.decoder = user_session.encoder
            user_session.encoder = random_hex(32)
            # log_message('Keys rotated', presto_user)
            
        user_session.last_action = timezone.now()
        if not user_session.active_role:
            user_session.active_role = user_profile.roles.all().first()
        user_session.save()
                
    # create the context dictionary
    context = {
        'base_url': base_url,
        'user': presto_user,
        'user_profile': user_profile,
        'user_name': user_name,
        'user_session': user_session,
        'user_roles': user_roles,
        'notifications': notifications,
        'page_title': 'Project Estafettes',
        'page_content': 'Work in progress...',
    }
    if user_session:
        uss = loads(user_session.state)
        if 'course_student_id' in uss:
            # adding entries to the context dictionary permits simple testing and rendering
            context.update({'csid': uss['course_student_id'], 'alias': uss['alias']})
            # for demonstration users, also remove all roles except Student
            if is_demo_user(context):
                context['user_roles'] = (r for r in context['user_roles'] if r.name == 'Student')
            # NOTE: instructors can focus on one of their dummy users, but keep their instructor menu

    # signal whether user may be entitled to any awards
    if presto_user:
        # awards can be obtained only by participating in estafettes with badges and/or referees
        if Participant.objects.filter(student__user=presto_user).filter(
            Q(estafette__with_badges=True) | Q(estafette__with_referees=True)).count() > 0:
            context['user_with_awards'] = True

    # return the generic context dictionary
    return context


# returns True iff user is a demonstration user (i.e., non-staff and yet allowed multiple enrollments)
def is_demo_user(context):
    return context['user'].username == settings.DEMO_USER_NAME


# returns True iff user is a "focused" demonstration user
def is_focused_user(context):
    return 'alias' in loads(context['user_session'].state)


# returns True iff alias is valid, and adds warning to context if not valid
def validate_alias(context, alias):
    if match('^[a-zA-Z][a-zA-Z0-9\s\.\-\'\(\)]{5,15}$', alias):
        return True
    warn_user(
        context,
        'Invalid participant alias "{}"'.format(alias),
        """An alias must start with a letter, and be 6 to 15 characters long.
           <br>
           It may contain letters, digits, periods, hyphens, apostrophes,
           and single spaces."""
        )
    return False


# sets course student ID and alias in user's session state
def set_focus_and_alias(context, csid, alias, clear_sessions=False):
    # reduce whitespace to single spaces, and trim trailing spaces
    alias = sub('\s+', ' ', alias).strip()
    # if resulting alias is invalid, warn user and return False 
    if not validate_alias(context, alias):
        return False
    # also warn user if alias is already in use
    if 'user' in context.keys() and context['user']:
        u_name = context['user'].username
    else:
        u_name = settings.DEMO_USER_NAME
    usl = UserSession.objects.filter(user__username=u_name)
    for us in usl:
        uss = loads(us.state)
        if 'alias' in uss and uss['alias'] == alias:
            # remove user "same alias" session records if told to do so 
            if clear_sessions:
                us.delete()
            else:
                warn_user(context, 'Alias "{}" already in use'.format(alias))
                return False
    # update user session state
    uss = loads(context['user_session'].state)
    uss['course_student_id'] = csid
    uss['alias'] = alias
    context['user_session'].state = dumps(uss)
    context['user_session'].save()
    # also add alias-related entries to context dictionary
    context.update({
        'csid': uss['course_student_id'],
        'alias': uss['alias']
        })
    # do not inform demonstration users, as they already get a dedicated dialog
    if context['user'].username != settings.DEMO_USER_NAME:
        inform_user(context, 'Now focused as "{}"'.format(alias))
    return True


# removes course student ID and alias from user's session state
def remove_focus_and_alias(context, csid):
    # update user session state
    uss = loads(context['user_session'].state)
    del uss['course_student_id']
    del uss['alias']
    context['user_session'].state = dumps(uss)
    context['user_session'].save()
    # also remove alias-related entries from context dictionary
    del context['csid']
    del context['alias']
    inform_user(context, 'Focus removed')
    return True


# adds qualification as referee for the given leg to the user's session state
def qualify_dummy_referee(context, leg):
    uss = loads(context['user_session'].state)
    # do this only when an alias has been set 
    if not ('alias' in uss):
        warn_user(context, 'Not focused - alias qualification denied')
        return False
    # qualifications are stored as a list of leg IDs
    if 'referee_legs' in uss:
        uss['referee_legs'].append(leg)
    else:
        uss.update({'referee_legs': [leg]})
    context['user_session'].state = dumps(uss)
    context['user_session'].save()
    return True


# checks whether the user (as identified in the context) can have the given role
# and if so, returns this role object
def has_role(context, role_name):
    return next((r for r in context['user_roles'] if r.name == role_name), None)


# if permitted, switches the user's role to the one specified
def change_role(context, new_role_name):
    role = has_role(context, new_role_name)
    if role:
        # change to the role and record this change in the context
        context['user_session'].active_role = role
        context['user_session'].save()
    return role


# returns tuple (error message, traceback) for given error object
def full_error_message(error):
    # NOTE: some error messages throw Unicode errors
    try:
        msg = str(error)
    except:
        # workaround is using only the first element
        try:
            msg = str(error[0])
        except:
            # should that fail, report why
            try:
                msg = str(sys.exc_info()[0])
            except:
                # and should that also fail, gracefully deal with this
                msg = '(non-stringable error)'
    # also guard against traceback errors
    try:
        trace = '\n'.join([tb for tb in traceback.format_tb(sys.exc_info()[2])])
    except:
        trace = '(failed to get traceback)'
    # return both strings as a tuple
    return (msg, trace)


# reports error as notification on an otherwise empty Presto user page
def report_error(context, error):
    msg, trace = full_error_message(error)
    # report expired session as an information message
    if msg == EXPIRED_SESSION_KEY:
        inform_user(context, msg, BACK_IN_BROWSER.format(context['base_url']))
    else:
        # add trace to notification only if user is admin
        if has_role(context, 'Administrator'):
            txt = trace
        else:
            txt = EXPIRED_MSG
        context['notifications'].append(['red', 'warning sign', msg, txt])
        # always add trace to log file
        log_message(msg + ':\n' + trace, context['user'])
    # render the error page
    context['page_title'] = 'Presto Error'


# displays a warning (header + text) at the top of the next page that is rendered,
# and writes an entry in the log file (defaults to the warning header)
def warn_user(context, msg, txt='', log=''):
    context['notifications'].append(['orange', 'warning sign', msg, txt])
    if not log:
        log = msg
    log_message('[Warning] ' + log, context['user'])


# displays an information item (header + text) at the top of the next page that is rendered,
# and writes an entry in the log file (defaults to the warning header)
def inform_user(context, msg, txt='', log=''):
    context['notifications'].append(['blue', 'info circle', msg, txt])
    if not log:
        log = msg
    log_message('[Info] ' + log, context['user'])
