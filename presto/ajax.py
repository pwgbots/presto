# Software developed by Pieter W.G. Bots for the PrESTO project
# Code repository: https://github.com/pwgbots/presto
# Project wiki: http://presto.tudelft.nl/wiki

"""
Copyright (c) 2019 Delft University of Technology

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


# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db.models import F
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.http import HttpResponse
from django.template.loader import render_to_string

from .models import (
    Appeal, Assignment,
    CaseUpload, Course, CourseEstafette, CourseStudent,
    DEFAULT_DATE,
    Estafette, EstafetteCase, EstafetteLeg, EstafetteTemplate,
    ItemAssignment, ItemReview,
    Language, LetterOfAcknowledgement,
    NO_SESSION_KEY,
    Participant, PeerReview, PrestoBadge, Profile,
    QueuePicture, QuestionnaireTemplate,
    Role,
    UserDownload, UserSession
)

# python modules
from binascii import a2b_base64
from datetime import datetime
from json import dumps, loads
from io import BytesIO
from PIL import Image
from random import randrange
from StringIO import StringIO

import os
import sys
import traceback

# presto modules
from presto.badge import verify_certified_image
from presto.generic import authenticated_user
from presto.history_view import set_history_properties
from presto.plag_scan import scan_assignment
from presto.utils import (decode, encode, half_points, log_message, prefixed_user_name,
    string_to_datetime, DATE_FORMAT, DATE_TIME_FORMAT, EDIT_STRING, FACES)

ANONYMOUS_ACTIONS = ['test badge', 'authenticate letter']

ANY_ROLE_ACTIONS = ['validate date', 'validate datetime'] + ANONYMOUS_ACTIONS

DEVELOPER_ACTIONS = ['get templates', 'get template', 'modify template', 'get step',
    'modify step', 'new item', 'modify item', 'reorder item', 'delete item', 'publish template',
    'list template editor', 'add template editor', 'remove template editor',
    'withdraw template', 'export template', 'import template']

ESTAFETTE_ACTIONS = ['modify estafette', 'modify case', 'publish estafette', 'withdraw estafette',
    'list case editor', 'add case editor', 'remove case editor']

INSTRUCTOR_ACTIONS = ['new estafette', 'get estafette', 'modify estafette', 'get case',
    'modify case', 'publish estafette', 'withdraw estafette', 'get course', 'modify course',
    'modify badge', 'list instructor', 'add instructor', 'remove instructor',
    'list case editor', 'add case editor', 'remove case editor',
    'unique relay', 'participant scan', 'participant history',
    'toggle pq', 'rotate picture']

STUDENT_ACTIONS = ['enroll', 'save assignment item', 'check review', 'save review',
    'save review item', 'save appraisal', 'save improvement appraisal', 'save decision']

TEMPLATE_ACTIONS = ['modify template', 'publish template', 'withdraw template', 'modify step',
    'list template editor', 'add template editor', 'remove template editor']

VALID_ACTIONS = ANY_ROLE_ACTIONS + STUDENT_ACTIONS + INSTRUCTOR_ACTIONS + DEVELOPER_ACTIONS


# "pseudo-view" (not using a template) that responds to Ajax requests
@method_decorator(csrf_exempt, name='dispatch')
def ajax(request, **kwargs):
    # jd is the dictionary to be returned as a JSON string
    jd = {}

    # POST parameter a specifies the action to be taken
    a = request.POST.get('a', '')
    if not a in VALID_ACTIONS:
        jd['error'] = 'Invalid action: "%s"' % a
        return HttpResponse(dumps(jd), content_type='text/plain')

    # authenticate user only if needed
    if not a in ANONYMOUS_ACTIONS: 
        # and then only get essential user specifics
        try:
            presto_user = authenticated_user(request)
            # only "demonstration users" can have multiple concurrent sessions
            if presto_user.username == settings.DEMO_USER_NAME:
                key = request.session.session_key
            else:
                key = NO_SESSION_KEY
            user_session, created = UserSession.objects.get_or_create(user=presto_user, session_key=key)
            user_roles = [r.name for r in presto_user.profile.roles.all()]
        except Exception, e:
            jd['error'] = 'No access -- ' + str(e)  # NOTE: DO NOT ADD str(e) AFTER TESTING
            return HttpResponse(dumps(jd), content_type='text/plain')

    # verify privileges
    if ((a in STUDENT_ACTIONS and not 'Student' in user_roles) or
        (a in INSTRUCTOR_ACTIONS and not 'Instructor' in user_roles) or
        (a in DEVELOPER_ACTIONS and not 'Developer' in user_roles)
    ):
        jd['error'] = 'Access denied'
        return HttpResponse(dumps(jd), content_type='text/plain')

    # process posted data
    # NOTE: Since AJAX calls do not refresh a page, the session hex codes are not rotated!
    #       This means that encoded keys must be decoded using the *encoder* field! 
    try:
        if a == 'validate date': 
            jd['dt'] = string_to_datetime(request.POST.get('s', ''))
            # only the date is asked for => strip the time part
            if jd['dt']:
                jd['dt'] = jd['dt'][0:10]
        elif a == 'validate datetime': 
            jd['dt'] = string_to_datetime(request.POST.get('s', ''))
        elif a == 'test badge':
            # by default, assume the image is NOT valid
            jd['r'] = 'INVALID'
            # get the URI-encoded image data
            b64 = request.POST.get('img', '')
            if b64:
                # get the parameter substrings
                b64 = b64.split(',')
                enc = b64[0].split(';')
                # check the encoding
                if len(enc) == 2 and enc[1] == 'base64':
                    # get the image data as raw IO bytes
                    bio = BytesIO(a2b_base64(b64[1]))
                    bio.seek(0)
                    # this data should then be readable for PIL
                    img = Image.open(bio)
                    # verify that the image is a valid badge
                    badge = verify_certified_image(img)
                    # if so, return the validation plus the badge properties
                    if badge:
                        jd['r'] = 'VALID'
                        jd.update(badge.as_dict())
                        # also add the learning goals for the completed step
                        jd['lg'] = EstafetteLeg.objects.filter(number=badge.attained_level,
                            template__id=jd['TID']).first().learning_objectives
                        # only log successful authentications, as failures log their error message
                        log_message('Badge authenticated for %s' % jd['FN'])
        elif a == 'authenticate letter':
            # by default, assume the authentication code is NOT valid
            jd['r'] = 'INVALID'
            c = request.POST.get('c', '')
            # authentication codes are 32 digit hexadecimal numbers
            if len(c) == 32:
                # verify that letter exists
                loa = LetterOfAcknowledgement.objects.filter(authentication_code=c)
                # if so, return the validation plus the LoA properties
                if loa:
                    jd['r'] = 'VALID'
                    loa = loa.first()
                    jd.update(loa.as_dict())
                    loa.verification_count += 1
                    loa.time_last_verified = timezone.now()
                    loa.save()
            # log all attempts
            if jd['r'] == 'VALID':
                log_message('LoA authenticated for %s' % jd['FN'])
            else:
                log_message('LoA authentication failed: no match for code "%s"' % c)
        elif a == 'enroll':
            cid = decode(request.POST.get('h', ''), user_session.encoder)
            c = Course.objects.get(pk=cid)
            cs = CourseStudent(course=c, user=presto_user,
                time_enrolled=timezone.now(), last_action=timezone.now())
            cs.save()
            log_message('AJAX: Enrolled in course ' + unicode(c), presto_user)
        elif a == 'save assignment item':
            aid = decode(request.POST.get('h', ''), user_session.encoder)
            ua = Assignment.objects.get(pk=aid)
            i = ua.leg.upload_items.get(number=request.POST.get('i', ''))
            ia, created = ItemAssignment.objects.get_or_create(assignment=ua, item=i)
            ia.rating = request.POST.get('r', '')
            ia.comment = request.POST.get('c', '')
            ia.save()
            log_message('Assignment item saved: ' + unicode(ia), presto_user)
            # calculate minutes since the assignment was assigned
            m = int((timezone.now() - ua.time_assigned).total_seconds() / 60) + 1
            jd['mtw'] = int(ua.leg.min_review_minutes - m)
            # also return whether review meets all conditions to be submitted
            if jd['mtw'] > 0:
                jd['sub'] = False
                log_message('Still %d minutes to wait' % jd['mtw'], presto_user)
            else:
                jd['sub'] = ua.is_complete()
        elif a in ['check review', 'save review', 'save review item']:
            prid = decode(request.POST.get('h', ''), user_session.encoder)
            pr = PeerReview.objects.get(pk=prid)
            if a == 'save review':
                pr.grade = request.POST.get('rr', '')
                pr.grade_motivation = request.POST.get('r', '')
                # NOTE: time_submitted is not set => saved, but not submitted yet
                pr.save()
                log_message('Review saved: ' + unicode(pr), presto_user)
            elif a == 'save review item':
                i = pr.assignment.leg.review_items.get(number=request.POST.get('i', ''))
                ir, created = ItemReview.objects.get_or_create(review=pr, item=i)
                ir.rating = request.POST.get('r', '')
                ir.comment = request.POST.get('c', '')
                ir.save()
                log_message('Review item saved: ' + unicode(ir), presto_user)
            # return whether assignment may be rejected
            pr_a = pr.assignment
            jd['rej'] = pr_a.leg.rejectable 
            # also return minutes until min. review time since first download
            pr_r = pr.reviewer
            if pr_r.student.dummy_index < 0:
                # ensure that instructors do not have a minimum review time
                jd['mtw'] = 0
            else:
                # calculate minutes since the work has been downloaded
                # NOTE: if no download, us the time the step was assigned
                ud = UserDownload.objects.filter(user=pr_r.student.user, assignment=pr_a).first()
                if ud:
                    t = ud.time_downloaded
                else:
                    t = pr_a.time_assigned
                m = int((timezone.now() - t).total_seconds() / 60) + 1
                jd['mtw'] = int(pr_a.leg.min_review_minutes - m)
            # also return whether review meets all conditions to be submitted
            if jd['mtw'] > 0:
                jd['sub'] = False
                log_message('Still %d minutes to wait' % jd['mtw'], presto_user)
            else:
                jd['sub'] = pr.is_complete()
        elif a == 'save appraisal':
            oid = decode(request.POST.get('h', ''), user_session.encoder)
            appraiser = int(request.POST.get('apt', 0))
            if appraiser == 0:  # review appraisal
                pr = PeerReview.objects.get(pk=oid)
                pr.appraisal = int(request.POST.get('ra', 0))
                pr.appraisal_comment = request.POST.get('ac', '')
                # NOTE: time_appraised is not set => saved, but not submitted yet
                pr.save()
                log_message('Review appraisal saved: ' + unicode(pr), presto_user)
            else:  # referee decision appraisal
                ap = Appeal.objects.get(pk=oid)
                if appraiser == 1:  # predecessor's appraisal of the referee decision
                    ap.predecessor_appraisal = int(request.POST.get('ra', 0))
                    ap.predecessor_motivation = request.POST.get('ac', '')
                    ap.save()
                    log_message('Predecessor response to referee decision saved: ' + unicode(ap), presto_user)
                else:
                    ap.successor_appraisal = int(request.POST.get('ra', 0))
                    ap.successor_motivation = request.POST.get('ac', '')
                    ap.save()
                    log_message('Successor response to referee decision saved: ' + unicode(ap), presto_user)
        elif a == 'save improvement appraisal':
            oid = decode(request.POST.get('h', ''), user_session.encoder)
            pr = PeerReview.objects.get(pk=oid)
            pr.improvement_appraisal = int(request.POST.get('ri', 0))
            pr.improvement_appraisal_comment = request.POST.get('ic', '')
            pr.save()
            log_message('Improvement appraisal (%d) saved: %s' % (pr.improvement_appraisal, unicode(pr)), presto_user)
        elif a == 'save decision':
            apid = decode(request.POST.get('h', ''), user_session.encoder)
            ap = Appeal.objects.get(pk=apid)
            ap.grade = int(request.POST.get('dr', 0))
            ap.grade_motivation = request.POST.get('dm', '')
            # print ap.grade_motivation
            ap.predecessor_penalty = float(request.POST.get('pp', 0))
            ap.successor_penalty = float(request.POST.get('sp', 0))
            # NOTE: time_decided is not set => saved, but not submitted yet
            ap.save()
            jd['pt'] = ap.review.reviewer.student.course.language.penalties_as_text(
                ap.predecessor_penalty, ap.successor_penalty)
            log_message('Appeal decision saved: ' + unicode(ap), presto_user)
        elif a == 'get estafette':
            eid = decode(request.POST.get('h', ''), user_session.encoder)
            e = Estafette.objects.get(pk=eid)
            jd['n'] = e.name
            jd['d'] = e.description
            jd['e'] = EDIT_STRING % (prefixed_user_name(e.last_editor),
                timezone.localtime(e.time_last_edit).strftime(DATE_TIME_FORMAT))
            # also pass number of estafettes having this template (no deletion if cnt > 0)
            jd['cnt'] = CourseEstafette.objects.filter(estafette=e).count()
        elif a == 'get case':
            ecid = decode(request.POST.get('h', ''), user_session.encoder)
            ec = EstafetteCase.objects.get(pk=ecid)
            jd['n'] = ec.name
            jd['d'] = ec.description
            jd['k'] = ec.required_keywords
            jd['u'] = '' if ec.upload == None else ec.upload.original_name
            jd['e'] = EDIT_STRING % (prefixed_user_name(ec.last_editor),
                timezone.localtime(ec.time_last_edit).strftime(DATE_TIME_FORMAT))
            # also pass number of assignments having this case (case cannot be deleted if acnt > 0)
            jd['acnt'] = Assignment.objects.filter(case=ec).count()
        elif a == 'new estafette':
            etid = decode(request.POST.get('h', ''), user_session.encoder)
            et = EstafetteTemplate.objects.get(pk=etid)
            e = Estafette(template=et, name=request.POST.get('n', ''),
                description=request.POST.get('d', ''),
                creator=presto_user, time_created=timezone.now(),
                last_editor=presto_user, time_last_edit=timezone.now())
            e.save()
        elif a == 'unique relay':
            cid = decode(request.POST.get('h', ''), user_session.encoder)
            eid = decode(request.POST.get('r', ''), user_session.encoder)
            suf = request.POST.get('s', '').strip()
            jd['cnt'] = CourseEstafette.objects.filter(course=Course.objects.get(pk=cid),
                estafette=Estafette.objects.get(pk=eid), suffix=suf).count()
        elif a == 'get course':
            cid = decode(request.POST.get('h', ''), user_session.encoder)
            c = Course.objects.get(pk=cid)
            # add all course attributes
            set_course_json(c, jd)
        elif a == 'modify course':
            cid = decode(request.POST.get('h', ''), user_session.encoder)
            c = Course.objects.get(pk=cid)
            c.name = request.POST.get('n', '')
            c.description = request.POST.get('d', '')
            l = Language.objects.filter(code=request.POST.get('lc', ''))
            if l:
                c.language = l.first()
            c.start_date = datetime.strptime(request.POST.get('sd', ''), '%Y-%m-%d')
            c.end_date = datetime.strptime(request.POST.get('ed', ''), '%Y-%m-%d')
            c.staff_name = request.POST.get('sn', '')
            c.staff_position = request.POST.get('sp', '')
            c.is_edX = request.POST.get('edx', '') == 'true'
            c.is_hidden = request.POST.get('hide', '') == 'true'
            c.save()
            # add all course attributes
            set_course_json(c, jd)
        elif a == 'modify badge':
            cid = decode(request.POST.get('h', ''), user_session.encoder)
            c = Course.objects.get(pk=cid)
            # double-check whether no badges exist for this course yet
            if (PrestoBadge.objects.filter(course=c).count() == 0
            # but always allow administrator to change badges
            or 'Developer' in user_roles):
                c.badge_color = int(request.POST.get('bc', ''))
                c.save()
            else:
                jd['error'] = 'Cannot change badge design because course badges have been issued'
        elif a in ['list instructor', 'add instructor', 'remove instructor']:
            cid = decode(request.POST.get('h', ''), user_session.encoder)
            c = Course.objects.get(pk=cid)
            # prevent error messages when instructor hex is not passed
            i = request.POST.get('i', '')
            if a != 'list instructor' and len(i) == 32:
                uid = decode(i, user_session.encoder)
                u = User.objects.get(pk=uid)
                if a == 'add instructor':
                    c.instructors.add(u)
                else:
                    c.instructors.remove(u)
                c.save()
            jd['il'] = [{'hex': encode(i.pk, user_session.encoder), 'name': prefixed_user_name(i)}
                for i in c.instructors.all()]
        elif a == 'toggle pq':
            cid = decode(request.POST.get('h', ''), user_session.encoder)
            c = Course.objects.get(pk=cid)
            p = request.POST.get('p', '')
            if p == 'open':
                c.picture_queue_open = not c.picture_queue_open
                c.save()
                jd['p'] = c.picture_queue_open
            elif p == 'strict':
                c.picture_queue_strict = not c.picture_queue_strict
                c.save()
                jd['p'] = c.picture_queue_strict
        elif a == 'rotate picture':
            qpid = decode(request.POST.get('h', ''), user_session.encoder)
            qp = QueuePicture.objects.get(pk=qpid)
            deg = request.POST.get('d', 0)
            # only rotate +/- 90 degrees
            if abs(int(deg)) == 90:
                original = StringIO(qp.picture.read())
                rotated = StringIO()
                image = Image.open(original)
                image = image.rotate(int(deg), expand=True)
                image.save(rotated, 'JPEG')
                old_path = qp.picture.path
                qp.picture.save(qp.picture.path, ContentFile(rotated.getvalue()))
                qp.save()
                os.remove(old_path)
                # NOTE: re-encode => hex is different => browser will not load image from cache
                jd['hex'] = encode(qpid, user_session.encoder)
            else:
                jd['hex'] = request.POST.get('h', '')
        elif a in ESTAFETTE_ACTIONS:
            # infer the concerned template from the hex ID
            if a == 'modify case':
                # hex encodes estafette case ID
                ecid = decode(request.POST.get('h', ''), user_session.encoder)
                ec = EstafetteCase.objects.get(pk=ecid)
                e  = ec.estafette
            else: 
                # hex encodes estafette ID
                eid = decode(request.POST.get('h', ''), user_session.encoder)
                e = Estafette.objects.get(pk=eid)
            if a == 'modify estafette':
                e.name = request.POST.get('n', '')
                e.description = request.POST.get('d', '')
                jd['n'] = e.name
                jd['d'] = e.description
                jd['e'] = EDIT_STRING % (prefixed_user_name(e.last_editor),
                    timezone.localtime(e.time_last_edit).strftime(DATE_TIME_FORMAT))
                # also pass number of estafettes having this template (no deletion if cnt > 0)
                jd['cnt'] = CourseEstafette.objects.filter(estafette=e).count()
            elif a == 'publish estafette':
                e.published = True
                log_message('Published estafette ' + e.name, presto_user)
            elif a == 'withdraw estafette':
                e.published = False
                log_message('Withdrawn template ' + e.name, presto_user)
            elif a in ['list case editor', 'add case editor', 'remove case editor']:
                # prevent error messages when instructor hex is not passed
                ed = request.POST.get('ed', '')
                if a != 'list case editor' and len(ed) == 32:
                    uid = decode(ed, user_session.encoder)
                    u = User.objects.get(pk=uid)
                    if a == 'add case editor':
                        e.editors.add(u)
                    else:
                        e.editors.remove(u)
                    e.save()
                jd['eds'] = [{'hex': encode(ed.pk, user_session.encoder), 'name': prefixed_user_name(ed)}
                    for ed in e.editors.all()]
            elif a == 'modify case':
                ec.name = request.POST.get('n', '')
                ec.description = request.POST.get('d', '')
                ec.required_keywords = request.POST.get('k', '')
                jd['n'] = ec.name
                jd['d'] = ec.description
                jd['k'] = ec.required_keywords
                ec.last_editor = presto_user
                ec.time_last_edit = timezone.now()
                ec.save()
                if request.POST.get('r') == 'true' and ec.upload != None:
                    ec.upload = None
                    ec.save()
                    # get primary keys of all case uploads associated with cases
                    cuids = EstafetteCase.objects.filter(
                        upload__isnull=False).values_list('upload__id', flat=True)
                    # clean up all unused instances of CaseUpload
                    not_used = CaseUpload.objects.exclude(id__in=cuids)
                    # first remove the uploaded files ...
                    for cu in not_used:
                        os.remove(cu.upload_file.path)
                    # ... and then delete the records from the database
                    not_used.delete()
                jd['e'] = EDIT_STRING % (prefixed_user_name(ec.last_editor),
                    timezone.localtime(ec.time_last_edit).strftime(DATE_TIME_FORMAT))
                f = request.FILES
                if f:
                    f = f['u']
                    upload_size = f.size / 1048576.0 # size in MB 
                    log_message('Case attachment upload file size: %3.2f MB' % upload_size, presto_user)
                    file_too_big = upload_size > settings.MAX_UPLOAD_SIZE
                    if file_too_big:  # NOTE: opening very large files may generate timeout!
                        jd['error'] = 'Upload file size (%3.2f MB) exceeds limit of %3.2f MB' % (
                            upload_size, settings.MAX_UPLOAD_SIZE)
                    else:
                        log_message('Uploaded file "%s" as attachment for estafette case %s' % (
                            f.name, unicode(ec)), presto_user)
                        ec.upload = CaseUpload.objects.create(
                            estafette=ec.estafette, upload_file=f, original_name=f.name)
                        ec.save()
                jd['u'] = '' if ec.upload == None else ec.upload.original_name
            # also update modification time of estafette if case has been modified
            e.last_editor = presto_user
            e.time_last_edit = timezone.now()
            e.save()
            jd['e'] = EDIT_STRING % (prefixed_user_name(e.last_editor),
                timezone.localtime(e.time_last_edit).strftime(DATE_TIME_FORMAT))
        elif a == 'get templates':
            # pass list of published templates
            tl = EstafetteTemplate.objects.filter(published=True)
            jd['tl'] = [{
                'id': encode(t.id, user_session.encoder),
                'title': t.name,
                'description': t.description
                } for t in tl]
        elif a in TEMPLATE_ACTIONS:
            # infer the concerned template from the hex ID
            if a == 'modify step':
                # hex encodes estafette leg ID
                elid = decode(request.POST.get('h', ''), user_session.encoder)
                el = EstafetteLeg.objects.get(pk=elid)
                et  = el.template
            else:
                # hex encodes template ID
                etid = decode(request.POST.get('h', ''), user_session.encoder)
                et = EstafetteTemplate.objects.get(pk=etid)
            if a == 'modify template':
                et.name = request.POST.get('n', '')
                et.description = request.POST.get('d', '')
                jd['n'] = et.name
                jd['d'] = et.description
                # also pass number of estafettes having this template (no deletion if cnt > 0)
                jd['cnt'] = Estafette.objects.filter(template=et).count()
                log_message('Modified template ' + et.name, presto_user)
            elif a == 'publish template':
                et.published = True
                log_message('Published template ' + et.name, presto_user)
            elif a == 'withdraw template':
                et.published = False
                log_message('Withdrawn template ' + et.name, presto_user)
            elif a in ['list template editor', 'add template editor', 'remove template editor']:
                # prevent error messages when developer hex is not passed
                ed = request.POST.get('ed', '')
                if a != 'list template editor' and len(ed) == 32:
                    uid = decode(ed, user_session.encoder)
                    u = User.objects.get(pk=uid)
                    if a == 'add template editor':
                        et.editors.add(u)
                    else:
                        et.editors.remove(u)
                    et.save()
                jd['eds'] = [{'hex': encode(ed.pk, user_session.encoder), 'name': prefixed_user_name(ed)}
                    for ed in et.editors.all()]
            elif a == 'modify step':
                tab = request.POST.get('t', '')  # t specifies the edited tab
                if tab == 'step':
                    el.name = request.POST.get('n', '')
                    el.rejectable = (request.POST.get('r', '') == 'true')
                    el.description = request.POST.get('d', '')
                    el.learning_objectives = request.POST.get('lo', '')
                elif tab == 'upload':
                    el.upload_instruction = request.POST.get('i', '')
                    el.required_files = request.POST.get('f', '')
                    el.required_section_title = request.POST.get('s', '')
                    el.required_section_length = request.POST.get('l', 0)
                    el.required_keywords = request.POST.get('k', '')
                    el.min_upload_minutes = request.POST.get('u', 0)
                elif tab == 'review':
                    el.review_instruction = request.POST.get('i', '')
                    el.review_model_text = request.POST.get('m', '')
                    el.word_count = request.POST.get('w', 0)
                    el.min_review_minutes = request.POST.get('r', 0)
                el.last_editor = presto_user
                el.time_last_edit = timezone.now()
                el.save()
                set_leg_json(el, jd)
                log_message('Modified step %s of template %s' % (el.name, et.name), presto_user)
            et.last_editor = presto_user
            et.time_last_edit = timezone.now()
            et.save()
            jd['te'] = EDIT_STRING % (prefixed_user_name(et.last_editor),
                timezone.localtime(et.time_last_edit).strftime(DATE_TIME_FORMAT))
        elif a == 'get template':
            etid = decode(request.POST.get('h', ''), user_session.encoder)
            et = EstafetteTemplate.objects.get(pk=etid)
            jd['n'] = et.name
            jd['d'] = et.description
            jd['te'] = EDIT_STRING % (prefixed_user_name(et.last_editor),
                timezone.localtime(et.time_last_edit).strftime(DATE_TIME_FORMAT))
            # also pass number of estafettes having this template (no deletion if cnt > 0)
            jd['cnt'] = Estafette.objects.filter(template=et).count()
        elif a == 'export template':
            etid = decode(request.POST.get('h', ''), user_session.encoder)
            et = EstafetteTemplate.objects.get(pk=etid)
            jd['tj'] = et.to_JSON()
            log_message('Exported template %s' % et.name, presto_user)
        elif a == 'import template':
            tj = request.POST.get('tj', '')
            # check whether JSON string is valid and includes essential template attributes
            d = loads(tj)
            if all (k in d for k in ('name', 'description', 'default_rules', 'legs')):
                et = EstafetteTemplate()
                et.init_from_JSON(tj, presto_user)
            else:
                raise ValueError('JSON string is not a valid template')
        elif a in ['get step', 'new item', 'modify item', 'reorder item', 'delete item']:
            elid = decode(request.POST.get('h', ''), user_session.encoder)
            el = EstafetteLeg.objects.get(pk=elid)
            # NOTE: by default, affected items are REVIEW items
            # print request.POST.get('ric', 'true')
            if request.POST.get('ric') == 'true':
                its = el.review_items
                icat = 'review'
            else:
                its = el.upload_items
                icat = 'upload'
            if a == 'new item':
                n = len(its.all()) + 1
                i = its.create(number = n,
                    name = request.POST.get('n', ''),
                    instruction = request.POST.get('i', ''),
                    word_count = request.POST.get('w', ''),
                    appraisal = request.POST.get('ap', ''))
                i.save()
                log_message('Added %s item #%d to leg %s' % (icat, n, unicode(el)), presto_user)
            elif a == 'modify item':
                n = int(request.POST.get('nr', 0))
                its.filter(number=n).update(
                    name = request.POST.get('n', ''),
                    instruction = request.POST.get('i', ''),
                    word_count = request.POST.get('w', ''),
                    appraisal = request.POST.get('ap', '')
                )
                log_message('Modifed %s item #%d of leg %s' % (icat, n, unicode(el)), presto_user)
            elif a == 'reorder item':
                n = int(request.POST.get('nr', ''))
                nn = n + int(request.POST.get('d', 0))  # d = -1 to move up, d = 1 to move down
                ri = its.get(number=n)
                swap = its.get(number=nn)
                ri.number = nn
                ri.save()
                swap.number = n
                swap.save()
                log_message('Renumbered %s item %s from %d to %d' % (icat, ri.name, n, nn), presto_user)
            elif a == 'delete item':
                n = int(request.POST.get('nr', ''))
                its.filter(number=n).delete()
                its.filter(number__gt=n).update(number=F('number') - 1)
                log_message('Removed %s item #%d from leg %s' % (icat, n, unicode(el)), presto_user)
            set_leg_json(el, jd)
        elif a == 'participant history':
            hx = request.POST.get('h', '')
            pid = decode(hx, user_session.encoder)
            p = Participant.objects.get(pk=pid)
            context = {'user': presto_user, 'user_session': user_session, 'identify': True,
                'user_roles': presto_user.profile.roles.all()}
            # add data for progress bar
            context['things_to_do'] = p.things_to_do()
            # NOTE: context properties will include identities of participants
            set_history_properties(context, p)
            jd['pn'] = '<a href="student/imp/%s">%s</a>' % (hx, p.student.dummy_name())
            jd['pm'] = p.student.user.email
            jd['ph'] = render_to_string('participant_history.html', context)
        elif a == 'participant scan':
            # for time and other formatting; instructor views in English only!
            hx = request.POST.get('h', '')
            pid = decode(hx, user_session.encoder)
            p = Participant.objects.get(pk=pid)
            jd['pn'] = '<a href="student/imp/%s">%s</a>' % (hx, p.student.dummy_name())
            # initialize step properties for all steps (even if not yet performed)
            step_list = [{
                'nr': i,
                'letter': '?',
                'uploaded': False,
                'scan': ''
                } for i in range(1, p.estafette.estafette.template.nr_of_legs() + 1)]
            # print step_list
            # now add data on each step for which there exists an assignment for this participant
            # (excluding clones and rejected assignments)
            a_list = Assignment.objects.filter(participant=p
                ).filter(clone_of__isnull=True).exclude(is_rejected=True).order_by('leg__number')
            for a in a_list:
                step = a.leg.number - 1
                step_list[step]['letter'] = a.case.letter
                step_list[step]['uploaded'] = a.time_uploaded != DEFAULT_DATE
                # also add plagiarism scan
                step_list[step]['percentage'], sc = scan_assignment(a.id)
                step_list[step]['scan'] = sc.replace('">',
                    '"><span class="a-code">%d%s</span>&nbsp;&nbsp;' % (
                        a.leg.number, a.case.letter), 1)
            # print step_list
            context = {'steps': step_list}
            jd['ps'] = render_to_string('participant_scan.html', context)
                
    # catch any exceptions
    except Exception, e:
        jd['error'] = str(e) + '\n'.join([tb for tb in traceback.format_tb(sys.exc_info()[2])])
            
    # return dictionary as JSON string 
    return HttpResponse(dumps(jd), content_type='text/plain')


# auxiliary function that adds all editable leg properties to a dict
def set_leg_json(el, jd):
    jd['n'] = el.name
    jd['r'] = el.rejectable
    jd['d'] = el.description.replace('<img ', '<img class="ui large image" ')
    jd['lo'] = el.learning_objectives
    jd['ui'] = el.upload_instruction.replace('<img ', '<img class="ui large image" ')
    jd['uits'] = [ui.to_dict() for ui in el.upload_items.all()]
    jd['f'] = el.required_files
    jd['ff'] = el.file_list()
    jd['s'] = el.required_section_title
    jd['l'] = el.required_section_length
    jd['k'] = el.required_keywords
    jd['ut'] = el.min_upload_minutes
    jd['ri'] = el.review_instruction.replace('<img ', '<img class="ui large image" ')
    jd['rits'] = [ri.to_dict() for ri in el.review_items.all()]
    jd['w'] = el.word_count
    jd['rt'] = el.min_review_minutes
    jd['se'] = EDIT_STRING % (prefixed_user_name(el.last_editor),
        timezone.localtime(el.time_last_edit).strftime(DATE_TIME_FORMAT))
    # also pass number of assignments for this leg (leg cannot be deleted if acnt > 0)
    jd['acnt'] = Assignment.objects.filter(leg=el).count()

# auxiliary function that adds all editable course properties to a dict
def set_course_json(c, jd):
    jd['c'] = c.code
    jd['n'] = c.name
    jd['m'] = prefixed_user_name(c.manager)
    jd['d'] = c.description
    jd['lc'] = c.language.code
    jd['sd'] = c.language.fdate(c.start_date)
    jd['ed'] = c.language.fdate(c.end_date)
    jd['sdi'] = c.start_date.strftime('%Y-%m-%d')
    jd['edi'] = c.end_date.strftime('%Y-%m-%d')
    jd['sn'] = c.staff_name
    jd['sp'] = c.staff_position
    jd['bc'] = c.badge_color
    jd['edx'] = c.is_edX
    jd['hide'] = c.is_hidden
