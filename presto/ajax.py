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
from django.core.files.base import ContentFile
from django.db.models import F
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.http import HttpResponse
from django.template.loader import render_to_string

from .models import (
    Appeal,
    Assignment,
    CaseUpload,
    Course,
    CourseEstafette,
    CourseStudent,
    DEFAULT_DATE,
    Estafette,
    EstafetteCase,
    EstafetteLeg,
    EstafetteTemplate,
    ItemAssignment,
    ItemReview,
    Language,
    LetterOfAcknowledgement,
    NO_SESSION_KEY,
    Objection,
    Participant,
    PeerReview,
    PrestoBadge,
    Profile,
    QueuePicture,
    QuestionnaireTemplate,
    Referee,
    Role,
    SHORT_DATE,
    UserSession,
    )

# python modules
from binascii import a2b_base64
from datetime import datetime
from json import dumps, loads
from io import BytesIO, open as io_open_file, StringIO
from PIL import Image
from random import randrange

import os
import sys
import traceback

# presto modules
from presto.badge import verify_certified_image
from presto.generic import authenticated_user
from presto.history_view import set_history_properties
from presto.plag_scan import scan_assignment
from presto.teams import current_team, things_to_do, team_user_downloads
from presto.utils import (
    DATE_FORMAT,
    DATE_TIME_FORMAT,
    decode,
    EDIT_STRING,
    encode,
    half_points,
    log_message,
    prefixed_user_name,
    string_to_datetime,
    ui_img,
    )

ANONYMOUS_ACTIONS = ['test badge', 'authenticate letter']

ANY_ROLE_ACTIONS = ['validate date', 'validate datetime'] + ANONYMOUS_ACTIONS

DEVELOPER_ACTIONS = [
    'add template editor',
    'delete item',
    'export template',
    'get step',
    'get template',
    'get templates',
    'import template',
    'list template editor',
    'modify item',
    'modify step',
    'modify template',
    'new item',
    'publish template',
    'remove template editor',
    'reorder item',
    'withdraw template',
    ]

ESTAFETTE_ACTIONS = [
    'add case editor',
    'list case editor',
    'modify case',
    'modify estafette',
    'publish estafette',
    'remove case editor',
    'withdraw estafette',
    ]

INSTRUCTOR_ACTIONS = [
    'add case editor',
    'add instructor',
    'claim question',
    'get case',
    'get course',
    'get estafette',
    'get question',
    'list case editor',
    'list instructor',
    'modify badge',
    'modify case',
    'modify course',
    'modify estafette',
    'new estafette',
    'participant history',
    'participant scan',
    'publish estafette',
    'withdraw estafette',
    'remove instructor',
    'remove case editor',
    'rotate picture',
    'toggle pq',
    'unique relay',
    ]

STUDENT_ACTIONS = [
    'check review',
    'check review submitted',
    'enroll',
    'save appraisal',
    'save assignment item',
    'save decision',
    'save improvement appraisal',
    'save review',
    'save review item',
    'submit question',
    ]

TEMPLATE_ACTIONS = [
    'add template editor',
    'list template editor',
    'modify step',
    'modify template',
    'publish template',
    'remove template editor',
    'withdraw template',
    ]

VALID_ACTIONS = ANY_ROLE_ACTIONS + STUDENT_ACTIONS + INSTRUCTOR_ACTIONS + DEVELOPER_ACTIONS

QUESTION_HEADER = """
<div class="ui top attached secondary segment">
  <div>
    <div style="display: inline-block; width: 6em; font-weight: bold">Submitted:</div>
    <div style="display: inline-block">{}</div>
  </div>
  <div>
    <div style="display: inline-block; width: 6em; font-weight: bold">Team:</div>
    <div style="display: inline-block">{}</div>
  </div>
</div>
<div class="ui bottom attached segment">
{}
</div>
"""


@method_decorator(csrf_exempt, name='dispatch')
def ajax(request, **kwargs):
    """
    Returns a JSON string in response to an AJAX request.
    """
    # jd is the dict to be returned as a JSON string.
    jd = {}

    # Get the user's IP address from the request.
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        settings.USER_IP = x_forwarded_for.split(',')[0]
    else:
        settings.USER_IP = request.META.get('REMOTE_ADDR')

    # POST parameter a specifies the action to be taken.
    a = request.POST.get('a', '')
    if not (a in VALID_ACTIONS):
        print(VALID_ACTIONS)
        jd['error'] = 'Invalid action: "{}"'.format(a)
        return HttpResponse(dumps(jd), content_type='text/plain')

    # Authenticate user only if needed...
    if not a in ANONYMOUS_ACTIONS: 
        # ... and then only get essential user specifics.
        try:
            presto_user = authenticated_user(request)
            # Only "demonstration users" can have multiple concurrent sessions.
            if presto_user.username == settings.DEMO_USER_NAME:
                key = request.session.session_key
            else:
                key = NO_SESSION_KEY
            user_session, created = UserSession.objects.get_or_create(
                user=presto_user,
                session_key=key
                )
            user_roles = [r.name for r in presto_user.profile.roles.all()]
        except Exception as e:
            # TO DO: Remove detailed error message str(e) in production version
            jd['error'] = 'No access -- ' + str(e)
            return HttpResponse(dumps(jd), content_type='text/plain')

    # Verify user role privileges.
    if ((a in STUDENT_ACTIONS and not 'Student' in user_roles)
        or (a in INSTRUCTOR_ACTIONS and not 'Instructor' in user_roles)
        or (a in DEVELOPER_ACTIONS and not 'Developer' in user_roles)
        ):
        jd['error'] = 'Access denied'
        return HttpResponse(dumps(jd), content_type='text/plain')

    # Process posted data.
    # NOTE: Since AJAX calls do not refresh a page, the session hex codes
    #       must NOT be rotated! This means that encoded keys must be decoded
    #       using the ENcoder field. 
    try:
        if a == 'validate date': 
            jd['dt'] = string_to_datetime(request.POST.get('s', ''))
            # Only the date is asked for => strip the time part.
            if jd['dt']:
                jd['dt'] = jd['dt'][0:10]
        elif a == 'validate datetime': 
            jd['dt'] = string_to_datetime(request.POST.get('s', ''))
        elif a == 'test badge':
            # By default, assume the image is NOT valid.
            jd['r'] = 'INVALID'
            # Get the URI-encoded image data.
            b64 = request.POST.get('img', '')
            if b64:
                # Get the parameter substrings.
                b64 = b64.split(',')
                enc = b64[0].split(';')
                # Check the encoding.
                if len(enc) == 2 and enc[1] == 'base64':
                    # Get the image data as raw IO bytes.
                    bio = BytesIO(a2b_base64(b64[1]))
                    bio.seek(0)
                    # This data should then be readable for PIL.
                    img = Image.open(bio)
                    # Verify that the image is a valid badge.
                    badge = verify_certified_image(img)
                    # If so, return the validation plus the badge properties.
                    if badge:
                        jd['r'] = 'VALID'
                        jd.update(badge.as_dict())
                        # Also add the learning goals for the completed step.
                        jd['lg'] = EstafetteLeg.objects.filter(
                            number=badge.attained_level,
                            template__id=jd['TID']
                            ).first().learning_objectives
                        # Only log successful authentications, as failures
                        # will log their error message.
                        log_message('Badge authenticated for ' + jd['FN'])
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
                log_message('LoA authenticated for ' + jd['FN'])
            else:
                log_message(
                    'LoA authentication failed: no match for code "{}"'.format(c)
                    )
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
            # Calculate minutes since the assignment was assigned.
            m = int((timezone.now() - ua.time_assigned).total_seconds() / 60) + 1
            jd['mtw'] = int(ua.leg.min_review_minutes - m)
            # Also return whether review meets all conditions to be submitted.
            if jd['mtw'] > 0:
                jd['sub'] = False
                log_message(
                    'Still {} minutes to wait'.format(jd['mtw']),
                    presto_user
                    )
            else:
                jd['sub'] = ua.is_complete()
        elif a in ['check review', 'save review', 'save review item']:
            prid = decode(request.POST.get('h', ''), user_session.encoder)
            pr = PeerReview.objects.get(pk=prid)
            # NOTE: this check is called for before uploading to prevent conflicting actions
            #       when multiple users act on behalf of the same team
            if pr.time_submitted != DEFAULT_DATE:
                jd['error'] = pr.reviewer.student.course.language.phrase('Review_submitted_by_team')
            elif a == 'save review':
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
            # check if user is referee
            is_ref = Referee.objects.filter(user=presto_user, estafette_leg=pr_a.leg)
            # also return minutes until min. review time since first download
            pr_r = pr.reviewer
            if pr_r.student.dummy_index < 0 or is_ref:
                # ensure that instructors and referees do not have a minimum review time
                jd['mtw'] = 0
            else:
                # calculate minutes since the work has been downloaded
                # NOTE: if no download, us the time the step was assigned
                ud = team_user_downloads(pr_r, [pr_a.id]).first()
                if ud:
                    t = ud.time_downloaded
                else:
                    t = pr_a.time_assigned
                m = int((timezone.now() - t).total_seconds() / 60) + 1
                jd['mtw'] = int(pr_a.leg.min_review_minutes - m)
            # also return whether review meets all conditions to be submitted
            if jd['mtw'] > 0:
                jd['sub'] = False
                log_message('Still {} minutes to wait'.format(jd['mtw']), presto_user)
            else:
                jd['sub'] = pr.is_complete()
                log_message('Review complete: ' + unicode(jd['sub']), presto_user)
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
            log_message(
                'Improvement appraisal ({}) saved: {}'.format(
                    pr.improvement_appraisal,
                    unicode(pr)
                    ),
                presto_user
                )
        elif a == 'save decision':
            rh = request.POST.get('rh', '')
            # Field rh (referee ID hex) is passed to indicate that the decision
            # concerns an objection.
            if rh:
                refid = decode(rh, user_session.encoder)
                obid = decode(request.POST.get('h', ''), user_session.encoder)
                ob = Objection.objects.get(pk=obid)
                # Double-check that decision is authentic.
                if ob.referee.id == refid:
                    ob.grade = int(request.POST.get('dr', 0)) + int(request.POST.get('dpr', 0)) * 256
                    ob.grade_motivation = request.POST.get('dm', '')
                    ob.predecessor_penalty = float(request.POST.get('pp', 0))
                    ob.successor_penalty = float(request.POST.get('sp', 0))
                    # NOTE: time_decided is not set => saved, but not submitted yet
                    ob.save()
                    jd['pt'] = ob.appeal.review.reviewer.student.course.language.penalties_as_text(
                        ob.predecessor_penalty, ob.successor_penalty)
                    log_message('Objection decision saved: ' + unicode(ob), presto_user)
                else:
                    jd['error'] = 'Objection decision not authenticated'
                    log_message(
                        'Objection decision not authenticated ({} does not match {})'.format(
                            ob.referee.id,
                            refid
                            ),
                        presto_user
                        )
            else:
                apid = decode(request.POST.get('h', ''), user_session.encoder)
                ap = Appeal.objects.get(pk=apid)
                ap.grade = int(request.POST.get('dr', 0)) + int(request.POST.get('dpr', 0)) * 256
                ap.grade_motivation = request.POST.get('dm', '')
                # print ap.grade_motivation
                ap.predecessor_penalty = float(request.POST.get('pp', 0))
                ap.successor_penalty = float(request.POST.get('sp', 0))
                # NOTE: time_decided is not set => saved, but not submitted yet
                ap.save()
                jd['pt'] = ap.review.reviewer.student.course.language.penalties_as_text(
                    ap.predecessor_penalty, ap.successor_penalty)
                log_message('Appeal decision saved: ' + unicode(ap), presto_user)
        elif a == 'get question' or a == 'claim question':
            # NOTE: for now, questions are stored in files in the LOG directory
            # TO DO: implement this via the database!
            # TO DO: use QuestionID hex rather than question property string
            qid = request.POST.get('h', '')  # decode(... , user_session.encoder)
            qpl = qid.split(';')
            time_sent = datetime.strptime(qpl[1], '%Y%m%d%H%M').strftime(
                '%A, %d %B %Y, %H:%M'
                )
            case_letter = qpl[2]
            pids = [int(pid) for pid in qpl[3].split(',')]
            p_set = Participant.objects.filter(id__in=pids)
            path = os.path.join(
                settings.LOG_DIR,
                'Q_{}_{}.html'.format(qpl[0], qpl[1])
                )
            # Check whether file exists.
            if not os.path.exists(path):
                log_message(
                    'Question text file "{}" not found'.format(path),
                    presto_user
                    )
                jd['error'] = 'Question file not found'
            # Check whether at least one participant exists.
            elif not p_set.first():
                log_message(
                    'Participants #{} not recognized'.format(qpl[3]),
                    presto_user
                    )
                jd['error'] = 'Participants not recognized'
            else:
                # Get the message content (HTML).
                try:
                    with io_open_file(path, 'r', encoding='utf-8') as htmlfile:
                        html = htmlfile.read()
                except IOError:
                    log_message(
                        'Failed to read content from "{}"'.format(path),
                        presto_user
                        )
                    html = '<p>(failed to read content)</p>'                    
                if a == 'claim question':
                    # append instructor's user name to entry in file
                    path = os.path.join(
                        settings.LOG_DIR,
                        'RQL_{}.data'.format(p_set.first().estafette.id)
                        )
                    if os.path.exists(path):
                        try:
                            with io_open_file(path, 'rt', encoding='utf-8') as rqlfile:
                                lines = rqlfile.read().replace(qid, qid + ';' + presto_user.username)
                            with io_open_file(path, 'w', encoding='utf-8') as rqlfile:
                                rqlfile.write(lines)
                        except IOError:
                            log_message(
                                'Failed to update question entry in "{}"'.format(path),
                                presto_user
                                )
                            jd['error'] = 'Failed to claim question'
                else:
                    team = ', '.join([p.student.dummy_name() for p in p_set])
                    email = '; '.join([p.student.user.email for p in p_set])
                    html = QUESTION_HEADER.format(time_sent, team, html)
                jd['hex'] = qid
                jd['cl'] = case_letter
                jd['msg'] = html
                log_message('Formatted question to take on', presto_user)
        elif a == 'submit question':
            # verify that sender is a participant
            pid = decode(request.POST.get('h', ''), user_session.encoder)
            p = Participant.objects.get(pk=pid)
            # participant may be part of a team
            ct = current_team(p)
            # use participant's username as identifier
            un = p.student.user.username
            # NOTE: time stamp with minute precision only to prevent double submissions
            time_stamp = timezone.now().strftime('%Y%m%d%H%M')
            # get question text (as HTML)
            html = request.POST.get('q')
            
            # NOTE: for now, questions are stored in files in the LOG directory
            # TO DO: implement this via the database!
            
            # assume no exceptions
            ok = True
            path = os.path.join(
                settings.LOG_DIR, 'Q_{}_{}.html'.format(un, time_stamp)
                )
            # check if file already exists, as this might occur when user clicks twice on submit
            if os.path.exists(path):
                log_message('Question text file "{}" already exists'.format(path), presto_user)
                ok = False
            else:
                # write question text (HTML) to separate file
                try:
                    with io_open_file(path, 'a+', encoding='utf-8') as htmlfile:
                        htmlfile.write(html)
                except IOError:
                    log_message('Failed to write to "{}"'.format(path), presto_user)
                    ok = False
            if ok:
                # get the question properties: sender's user name, time stamp, case letter, team participant IDs
                case_letter = request.POST.get('c', '?')
                q_data = ';'.join([un, time_stamp, case_letter, ','.join([str(tp.id) for tp in ct])])
                # append question properties as one semicolon-separated line to the relay's question list
                path = os.path.join(settings.LOG_DIR, 'RQL_{}.data'.format(p.estafette.id))
                with io_open_file(path, 'a+', encoding='utf-8') as rqlfile:
                    rqlfile.write(q_data + '\n')
                lang = p.estafette.course.language
                jd['hdr'] = lang.phrase('Question_submitted')
                jd['qst'] = html
                jd['msg'] = lang.phrase('It_can_take_a_while')
                log_message('Submitted a question on case ' + case_letter, presto_user)

        elif a == 'get estafette':
            eid = decode(request.POST.get('h', ''), user_session.encoder)
            e = Estafette.objects.get(pk=eid)
            jd['n'] = e.name
            jd['d'] = e.description
            jd['e'] = EDIT_STRING.format(
                name=prefixed_user_name(e.last_editor),
                time=timezone.localtime(e.time_last_edit).strftime(DATE_TIME_FORMAT)
                )
            # also pass number of estafettes having this template (no deletion if cnt > 0)
            jd['cnt'] = CourseEstafette.objects.filter(estafette=e).count()
        elif a == 'get case':
            ecid = decode(request.POST.get('h', ''), user_session.encoder)
            ec = EstafetteCase.objects.get(pk=ecid)
            jd['n'] = ec.name
            jd['d'] = ui_img(ec.description)
            jd['k'] = ec.required_keywords
            jd['u'] = '' if ec.upload == None else ec.upload.original_name
            jd['e'] = EDIT_STRING.format(
                name=prefixed_user_name(ec.last_editor),
                time=timezone.localtime(ec.time_last_edit).strftime(DATE_TIME_FORMAT)
                )
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
            c.start_date = datetime.strptime(request.POST.get('sd', ''), SHORT_DATE)
            c.end_date = datetime.strptime(request.POST.get('ed', ''), SHORT_DATE)
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
                jd['e'] = EDIT_STRING.format(
                    name=prefixed_user_name(e.last_editor),
                    time=timezone.localtime(e.time_last_edit).strftime(DATE_TIME_FORMAT)
                    )
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
                jd['eds'] = [{
                    'hex': encode(ed.pk, user_session.encoder),
                    'name': prefixed_user_name(ed)
                    } for ed in e.editors.all()
                    ]
            elif a == 'modify case':
                ec.name = request.POST.get('n', '')
                ec.description = request.POST.get('d', '')
                ec.required_keywords = request.POST.get('k', '')
                jd['n'] = ec.name
                jd['d'] = ui_img(ec.description)
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
                jd['e'] = EDIT_STRING.format(
                    name=prefixed_user_name(ec.last_editor),
                    time=timezone.localtime(ec.time_last_edit).strftime(DATE_TIME_FORMAT)
                    )
                f = request.FILES
                if f:
                    f = f['u']
                    upload_size = f.size / 1048576.0 # size in MB 
                    log_message(
                        'Case attachment upload file size: {:3.2f} MB'.format(
                            upload_size
                            ),
                        presto_user
                        )
                    file_too_big = upload_size > settings.MAX_UPLOAD_SIZE
                    if file_too_big:  # NOTE: opening very large files may generate timeout!
                        jd['error'] = 'Upload file size ({:3.2f} MB) exceeds limit of {:3.2f} MB'.format(
                            upload_size,
                            settings.MAX_UPLOAD_SIZE
                            )
                    else:
                        log_message(
                            'Uploaded file "{}" as attachment for estafette case {}'.format(
                                f.name,
                                unicode(ec)
                                ),
                            presto_user
                            )
                        ec.upload = CaseUpload.objects.create(
                            estafette=ec.estafette,
                            upload_file=f,
                            original_name=f.name
                            )
                        ec.save()
                jd['u'] = '' if ec.upload == None else ec.upload.original_name
            # also update modification time of estafette if case has been modified
            e.last_editor = presto_user
            e.time_last_edit = timezone.now()
            e.save()
            jd['e'] = EDIT_STRING.format(
                name=prefixed_user_name(e.last_editor),
                time=timezone.localtime(e.time_last_edit).strftime(DATE_TIME_FORMAT)
                )
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
                log_message(
                    'Modified step {} of template {}'.format(el.name, et.name),
                    presto_user
                    )
            et.last_editor = presto_user
            et.time_last_edit = timezone.now()
            et.save()
            jd['te'] = EDIT_STRING.format(
                name=prefixed_user_name(et.last_editor),
                time=timezone.localtime(et.time_last_edit).strftime(DATE_TIME_FORMAT)
                )
        elif a == 'get template':
            etid = decode(request.POST.get('h', ''), user_session.encoder)
            et = EstafetteTemplate.objects.get(pk=etid)
            jd['n'] = et.name
            jd['d'] = et.description
            jd['te'] = EDIT_STRING.format(
                name=prefixed_user_name(et.last_editor),
                time=timezone.localtime(et.time_last_edit).strftime(DATE_TIME_FORMAT)
                )
            # also pass number of estafettes having this template (no deletion if cnt > 0)
            jd['cnt'] = Estafette.objects.filter(template=et).count()
        elif a == 'export template':
            etid = decode(request.POST.get('h', ''), user_session.encoder)
            et = EstafetteTemplate.objects.get(pk=etid)
            jd['tj'] = et.to_JSON()
            log_message('Exported template ' + et.name, presto_user)
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
                log_message(
                    'Added {} item #{} to leg {}'.format(icat, n, unicode(el)),
                    presto_user
                    )
            elif a == 'modify item':
                n = int(request.POST.get('nr', 0))
                its.filter(number=n).update(
                    name = request.POST.get('n', ''),
                    instruction = request.POST.get('i', ''),
                    word_count = request.POST.get('w', ''),
                    appraisal = request.POST.get('ap', '')
                )
                log_message(
                    'Modifed {} item #{} of leg {}'.format(icat, n, unicode(el)),
                    presto_user
                    )
            elif a == 'reorder item':
                n = int(request.POST.get('nr', ''))
                nn = n + int(request.POST.get('d', 0))  # d = -1 to move up, d = 1 to move down
                ri = its.get(number=n)
                swap = its.get(number=nn)
                ri.number = nn
                ri.save()
                swap.number = n
                swap.save()
                log_message(
                    'Renumbered {} item {} from {} to {}'.format(icat, ri.name, n, nn),
                    presto_user
                    )
            elif a == 'delete item':
                n = int(request.POST.get('nr', ''))
                its.filter(number=n).delete()
                its.filter(number__gt=n).update(number=F('number') - 1)
                log_message(
                    'Removed {} item #{} from leg {}'.format(icat, n, unicode(el)),
                    presto_user
                    )
            set_leg_json(el, jd)
        elif a == 'participant history':
            hx = request.POST.get('h', '')
            pid = decode(hx, user_session.encoder)
            p = Participant.objects.get(pk=pid)
            context = {
                'user': presto_user,
                'user_session': user_session,
                'identify': True,
                'user_roles': presto_user.profile.roles.all()
                }
            # add data for progress bar
            context['things_to_do'] = things_to_do(p)
            # NOTE: context properties will include identities of participants
            set_history_properties(context, p)
            jd['pn'] = '<a href="student/imp/{}">{}</a>'.format(
                hx,
                p.student.dummy_name()
                )
            jd['pm'] = p.student.user.email
            jd['ph'] = render_to_string('participant_history.html', context)
        elif a == 'participant scan':
            # for time and other formatting; instructor views in English only!
            hx = request.POST.get('h', '')
            pid = decode(hx, user_session.encoder)
            p = Participant.objects.get(pk=pid)
            jd['pn'] = '<a href="student/imp/{}">{}</a>'.format(hx, p.student.dummy_name())
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
                step_list[step]['scan'] = sc.replace(
                    '">',
                    '"><span class="a-code">{}{}</span>&nbsp;&nbsp;'.format(
                        a.leg.number, a.case.letter
                    ),
                    1
                    )
            # print step_list
            context = {'steps': step_list}
            jd['ps'] = render_to_string('participant_scan.html', context)
                
    # catch any exceptions
    except Exception as e:
        jd['error'] = str(e) + '\n'.join(
            [tb for tb in traceback.format_tb(sys.exc_info()[2])]
            )
            
    # return dictionary as JSON string 
    return HttpResponse(dumps(jd), content_type='text/plain')


# auxiliary function that adds all editable leg properties to a dict
def set_leg_json(el, jd):
    jd['n'] = el.name
    jd['r'] = el.rejectable
    jd['d'] = ui_img(el.description)
    jd['lo'] = el.learning_objectives
    jd['ui'] = ui_img(el.upload_instruction)
    jd['uits'] = [ui.to_dict() for ui in el.upload_items.all()]
    jd['f'] = el.required_files
    jd['ff'] = el.file_list()
    jd['s'] = el.required_section_title
    jd['l'] = el.required_section_length
    jd['k'] = el.required_keywords
    jd['ut'] = el.min_upload_minutes
    jd['ri'] = ui_img(el.review_instruction)
    jd['rits'] = [ri.to_dict() for ri in el.review_items.all()]
    jd['w'] = el.word_count
    jd['rt'] = el.min_review_minutes
    jd['se'] = EDIT_STRING.format(
        name=prefixed_user_name(el.last_editor),
        time=timezone.localtime(el.time_last_edit).strftime(DATE_TIME_FORMAT)
        )
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
    jd['sdi'] = c.start_date.strftime(SHORT_DATE)
    jd['edi'] = c.end_date.strftime(SHORT_DATE)
    jd['sn'] = c.staff_name
    jd['sp'] = c.staff_position
    jd['bc'] = c.badge_color
    jd['edx'] = c.is_edX
    jd['hide'] = c.is_hidden
