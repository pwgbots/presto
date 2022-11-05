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
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .models import (
    Appeal,
    Assignment, 
    Course,
    CourseEstafette,
    CourseStudent,
    DEFAULT_DATE, 
    EstafetteCase,
    EstafetteLeg,
    Language,
    LegVideo,
    MAX_DAYS_BEYOND_END_DATE,
    MINIMUM_INSTRUCTOR_WORD_COUNT,
    Participant,
    ParticipantUpload,
    PeerReview,
    Objection,
    Referee,
    STAR_DIVIDER,
    UserDownload
    )

# python modules
from datetime import datetime, timedelta
from docx import Document
from json import loads
from openpyxl import load_workbook
import os
from pptx import Presentation
from PyPDF2 import PdfFileReader
from tempfile import mkstemp

# presto modules
from presto.generic import (
    change_role,
    full_error_message,
    generic_context,
    has_role,
    inform_user,
    is_demo_user,
    is_focused_user,
    remove_focus_and_alias,
    report_error,
    set_focus_and_alias,
    warn_user
    )
from presto.plag_scan import scan_one_assignment
from presto.scan import (
    contains_comments,
    missing_key_words,
    missing_sections
    )
from presto.teams import (
    authorized_participant,
    current_team_leader,
    extended_assignment_deadline,
    extended_review_deadline,
    sometime_team_partners,
    team_appeals,
    team_as_html,
    team_assignments,
    team_final_reviews,
    team_user_downloads,
    things_to_do
    )
from presto.utils import (
    COLORS,
    DATE_TIME_FORMAT,
    decode,
    EDIT_STRING,
    encode,
    FACES,
    IMPROVEMENTS,
    log_message,
    OPINIONS,
    pdf_to_text,
    prefixed_user_name,
    random_hex,
    word_count,
    ui_img,
    YOUR_OPINIONS
    )


@method_decorator(csrf_exempt, name='dispatch')
@login_required(login_url=settings.LOGIN_URL)
def student(request, **kwargs):
    """
    Return the "home" view for the student role.
    """
    h = kwargs.get('hex', '')
    context = generic_context(request, h)
    
    # check whether user can have student role
    if not change_role(context, 'Student'):
        return render(request, 'presto/forbidden.html', context)
    try:
        # do whatever action is specified by the URL
        act = kwargs.get('action', '')
        if act == 'imp':
            # validate parameters
            if not has_role(context, 'Instructor'):
                log_message('[ERROR] Impersonation attempt by non-instructor', context['user'])
            else:
                pid = decode(h, context['user_session'].decoder)
                log_message('[Info] Impersonation by instructor', context['user'])
                context['user'] = Participant.objects.get(pk=pid).student.user
                log_message('[Info] Now impersonated by instructor', context['user'])
        elif act == 'enroll':
            # validate parameters
            cid = decode(h, context['user_session'].decoder)
            c = Course.objects.get(pk=cid)
            csl = CourseStudent.objects.filter(user=context['user']).filter(course=c)
            is_instructor = (has_role(context, 'Instructor')
                and (c.manager == context['user']
                     or c.instructors.filter(id=context['user'].id).exists())
                )
            if csl and not (is_instructor or is_demo_user(context)):
                lang = c.language
                warn_user(
                    context,
                    lang.phrase('Already_enrolled'),
                    lang.phrase('Enrolled_on').format(
                        course=c.title(),
                        time=lang.ftime(csl.first().time_enrolled)
                        ),
                    'Tried to enroll again in course ' + str(c)
                    )
            else:
                if csl:
                    # since user is known to be instructor or demo-user, add a dummy student
                    # with index one higher than the highest so far
                    # NOTE: if still only one (i.e., course manager having dummy index -1)
                    # n should be 1, hence the second max() function
                    n = max(1, max([cs.dummy_index for cs in csl]) + 1)
                elif is_instructor or is_demo_user(context):
                    n = 1  # "demo-students" and "instructor students" should always appear as "dummy"
                else:
                    n = 0
                log_message('TRACE - dummy index = {}'.format(n), context['user'])
                cs = CourseStudent(course=c,
                                   user=context['user'],
                                   dummy_index=n,
                                   time_enrolled=timezone.now(),
                                   last_action=timezone.now()
                                  )
                cs.save()
                lang = c.language
                inform_user(
                    context,
                    lang.phrase('Enrollment_succeeded'),
                    lang.phrase('You_have_enrolled').format(course=c.title()),
                    'Enrolled in course ' + str(c)
                    )
        # check whether focus is set on some "dummy" participant
        elif act == 'focus':
            pid = decode(h, context['user_session'].decoder)
            p = Participant.objects.get(pk=pid)
            p.time_started=timezone.now()
            p.time_last_action=timezone.now()
            p.save()
            ce = p.estafette
            if p.student.dummy_index > 0:
                set_focus_and_alias(
                    context,
                    p.student.id,
                    request.POST.get('alias', '')
                    )
                # NOTE: renew the context to effectuate the focus
                context = generic_context(request)
            else:
                warn_user(
                    context,
                    'Can focus on "dummy" participants only',
                    lang.phrase('Started_on').format(
                        relay=ce.title(),
                        time=lang.ftime(p.time_registered)
                        ),
                    'Tried to focus on non-dummy in ' + str(ce)
                    )
        # check whether focus on "dummy" participant should be removed
        elif act == 'defocus':
            pid = decode(h, context['user_session'].decoder)
            p = Participant.objects.get(pk=pid)
            p.time_last_action=timezone.now()
            p.save()
            ce = p.estafette
            # NOTE: double-check to prevent demonstration users from defocusing
            if p.student.dummy_index > 0 and not is_demo_user(context):
                remove_focus_and_alias(context, p.student.id)
                # NOTE: renew the context to effectuate the focus
                context = generic_context(request)
        # check whether student is starting an estafette
        elif act == 'start':
            pid = decode(h, context['user_session'].decoder)
            p = Participant.objects.get(pk=pid)
            dts = p.time_started
            if dts == DEFAULT_DATE:
                p.time_started=timezone.now()
            p.time_last_action=timezone.now()
            p.save()
            ce = p.estafette
            log_message('Starting with relay ' + str(ce), context['user'])
            lang = ce.course.language
            # do not let a student start again
            # NOTE: this should happpen only if user goes back in browser
            if dts > DEFAULT_DATE:
                warn_user(
                    context,
                    lang.phrase('Already_started'),
                    lang.phrase('Started_on').format(
                        relay=ce.title(),
                        time=lang.ftime(dts)
                        ),
                    'Tried to start again with ' + str(ce))
            # double-check that "instructor participants" cannot start
            elif p.student.dummy_index < 0:
                warn_user(
                    context,
                    'Instructor-participants should start as "dummy"',
                    'Please report this error to the Presto administrator.'
                    )
            elif team_assignments(p):
                inform_user(
                    context,
                    lang.phrase('Team_has_assignment'),
                    lang.phrase('Please_coordinate'),
                    'No new first step created for team participant '
                        + str(p)
                    )
            else:
                # needs a first assignment, so get the "rarest" case
                ec_list = EstafetteCase.objects.filter(estafette=ce.estafette)
                el_list = EstafetteLeg.objects.filter(template=ce.estafette.template)
                # just in case: check whether this estafette has legs and a case having number 1
                if ec_list and el_list.filter(number=1):
                    # count number of assignments for step 1 per case
                    ac_list = EstafetteCase.objects.filter(
                        assignment__participant__estafette=ce
                        ).filter(assignment__leg__number=1
                        ).annotate(a_count=Count('assignment', distinct=True)
                        ).order_by('a_count')
                    acc = ', '.join([ac.letter + str(ac.a_count) for ac in ac_list])
                    log_message('TRACE: Step 1 cases ' + acc , context['user'])
                    # see if there are still "unused" cases; if so, take the first
                    if len(ec_list) > len(ac_list):
                        ec = ec_list.exclude(
                            letter__in=[ac.letter for ac in ac_list]
                            ).first()
                    else:
                        ec = ac_list.first()
                    # see if participant is on a team
                    ctl = current_team_leader(p)
                    if ctl:
                        # if so, assign the first assignment to this participant
                        p = ctl
                    # create the assignment -- default fields suffice
                    a, created = Assignment.objects.get_or_create(participant=p,
                        case=ec, leg=el_list.first())
                    if not created:
                        log_message(
                            'WARNING: attempt to assign first step again '
                                + '(ID {})'.format(a.id),
                            context['user']
                            )
                    inform_user(
                        context,
                        lang.phrase('Started'),
                        lang.phrase('Godspeed'),
                        'Started relay ' + str(p.estafette)
                        )
        elif act == 'upload':
            # verify that upload is for an assignment made by the participant
            aid = decode(h, context['user_session'].decoder)
            a = Assignment.objects.get(pk=aid)
            if not authorized_participant(a.participant, context['user']):
                raise ValueError('Assignment not authenticated')
            a.participant.time_last_action=timezone.now()
            a.participant.save()
            lang = a.participant.estafette.course.language
            # assume that review of predecessor is complete,
            # or not required (step 1)
            rev_ok = True
            rev_sub = True
            # calculate time since user started with this assignment
            t_now = timezone.now()
            if a.predecessor:
                # check whether review of predecessor's work is complete
                pr = PeerReview.objects.filter(assignment=a.predecessor).first()
                rev_sub = pr and pr.time_submitted != DEFAULT_DATE
                rev_ok = pr and pr.is_complete()
                # use time of first download as start time
                tud = team_user_downloads(
                    a.participant,
                    [a.predecessor.id]
                    ).first()
                if tud:
                    # if downloaded, get the earliest date
                    t_started = tud.time_downloaded
                else:
                    # otherwise, use current time, as this will still work
                    # if zero waiting time
                    t_started = t_now
            else:
                # no predecessor => this was first step
                t_started = a.time_assigned
            # calculate how much time to wait still (in seconds)
            sec_since_start = (t_now - t_started).total_seconds()
            sec_to_wait = a.leg.min_upload_minutes * 60 - sec_since_start

            # check whether upload already took place
            if a.time_uploaded != DEFAULT_DATE:
                warn_user(
                    context,
                    lang.phrase('Already_submitted'),
                    lang.phrase('You_already_uploaded')
                    )
            # check whether sufficient time has passed -- allow half a minute margin
            # NOTE: this can appen if user edits in-browser HTML to enable the Upload button!
            elif sec_to_wait > 30:
                warn_user(
                    context,
                    lang.phrase('You_cannot_upload_yet'),
                    lang.phrase('Minimum_working_time')
                    )
            elif not rev_ok:
                warn_user(
                    context,
                    lang.phrase('You_cannot_upload_yet'),
                    lang.phrase('Peer_review_not_submitted')
                    )
            elif not rev_sub:
                warn_user(
                    context,
                    lang.phrase('You_cannot_upload_yet'),
                    lang.phrase('Incomplete_peer_review')
                    )
            else:
                # process required documents
                rfl = a.leg.file_list() 
                # first check whether uploaded files are valid
                ok = True
                try:
                    for rf in rfl:
                        file_ok = True
                        file_incomplete = False
                        file_too_big = False
                        f = request.FILES[rf['name']]
                        upload_size = f.size / 1048576.0 # size in MB 
                        log_message(
                            'Upload file size: {:3.2f} MB'.format(upload_size),
                            context['user']
                            )
                        file_too_big = upload_size > settings.MAX_UPLOAD_SIZE
                        ext = os.path.splitext(f.name)[1]
                        # types string has form ".ext1,.ext2,...", hence for
                        # find() to function correctly, a comma is added to
                        # both the types string and ext
                        if (rf['types'] + ',').find(ext + ',') < 0:
                            log_message(
                                'Warning: upload has invalid extension ' + ext,
                                context['user']
                                )
                            file_ok = False
                        elif not file_too_big:
                            # NOTE: opening very large files may generate timeout!
                            # actually open file to test whether it is of the right type
                            try:
                                # save upload as temporary file
                                handle, fn = mkstemp()
                                os.close(handle)
                                with open(fn, 'wb+') as dst:
                                    for chunk in f.chunks():
                                        dst.write(chunk)
                                # NOTE: openpyxl requires files to have a valid extension!
                                # NOTE: extension is always added for uniformity & tracing purposes
                                os.rename(fn, fn + ext)
                                fn += ext
                                # see if document contains comments
                                with_comments = contains_comments(fn)
                                # try to open the file with the correct application
                                if ext in ['.docx']:
                                    doc = Document(fn)
                                    # check whether document contains all required parts
                                    missing_kw = missing_key_words(a, doc)
                                    missing_sect = missing_sections(a, doc)
                                    file_incomplete = missing_kw or missing_sect
                                elif ext in ['.pptx']:
                                    prs = Presentation(fn)
                                elif ext in ['.xlsx']:
                                    wbk = load_workbook(fn)
                                elif ext == '.pdf':
                                    pdf = PdfFileReader(fn)
                                    # No error? Then extract text from PDF.
                                    ascii = pdf_to_text(fn)
                                    # Check text for required parts.
                                    missing_kw = missing_key_words(a, ascii)
                                    missing_sect = missing_sections(a, ascii)
                                    file_incomplete = missing_kw or missing_sect
                                    
                            # NOTE: assumes that incorrect file types will raise an error
                            except Exception as e:
                                log_message(
                                    'ERROR while checking file {}: {}'.format(
                                        fn,
                                        str(e)
                                        ),
                                    context['user']
                                    )
                                file_ok = False
                            # ALWAYS remove this copy, or it will bloat the tmp directory
                            os.remove(fn)
                        if not file_ok:
                            warn_user(
                                context,
                                lang.phrase('Invalid_file'),
                                lang.phrase('File_is_not_type').format(
                                    file=rf['name'],
                                    type=rf['types']
                                    )
                                )
                            ok = False
                        elif file_too_big:
                            warn_user(
                                context,
                                lang.phrase('File_too_big'),
                                lang.phrase('File_exceeds_limit').format(
                                    size=upload_size,
                                    max=settings.MAX_UPLOAD_SIZE
                                    )
                                )
                            ok = False
                        elif with_comments:
                            warn_user(
                                context,
                                lang.phrase('File_contains_comments'),
                                lang.phrase('How_to_remove_comments')
                                )
                            ok = False
                        elif file_incomplete:
                            if missing_sect:
                                warn_user(
                                    context,
                                    lang.phrase('Document_incomplete').format(
                                        doc=rf['name']
                                        ),
                                    missing_sect,
                                    'Upload with missing sections: '
                                        + missing_sect
                                    )
                            if missing_kw:
                                warn_user(
                                    context,
                                    lang.phrase('Missing_key_words'),
                                    lang.phrase(
                                        'Document_should_mention'
                                        ).format(
                                            doc=rf['name'],
                                            terms=missing_kw
                                            ),
                                    'Upload with missing keywords: '
                                        + missing_kw
                                    )
                            ok = False
                except Exception as e:
                    # catch any other errors
                    fem = full_error_message(e)
                    warn_user(
                        context,
                        lang.phrase('Upload_failed'),
                        lang.phrase('Missing_or_invalid_files'),
                        'ERROR during upload: {}\n{}'.format(fem[0], fem[1])
                        )
                    ok = False
                # only accept the upload if all files have been validated
                if ok:        
                    for rf in rfl:
                        f = request.FILES[rf['name']]
                        # no need to anonymize file (is done when downloading)
                        ParticipantUpload.objects.create(
                            assignment=a,
                            file_name=rf['name'],
                            upload_file=f
                            )
                        log_message(
                            'Uploaded file "{n}" as {f} for relay {r}'.format(
                                n=f.name,
                                f=rf['name'],
                                r=str(a.participant.estafette)
                                ),
                            context['user']
                            )
                    # update the assignment status in thread-safe manner
                    with transaction.atomic():
                        a.time_uploaded = timezone.now()
                        # NOTES:
                        # (1) If assignment A building on a "clone" is uploaded
                        #     BEFORE assignment B building on the original of
                        #     this clone, switch the predecessors of A and B so
                        #     that the predecessor of B gets to see the review
                        #     written by A.
                        # (2) This does not apply to "selfies" -- if A builds on
                        #     a "selfie" clone, the original work MUST keep on
                        #     waiting for a review, as the uploaded work + review
                        #     is authored by the same participant.
                        # (3) This operation is tricky, so we spell things out.
                        if (a.predecessor
                                and a.predecessor.clone_of
                                and not a.predecessor.is_selfie
                            ):
                            log_message(
                                'Predecessor is clone: '
                                    + str(a.predecessor),
                                context['user']
                                )
                            # remember that the uploader has reviewed this "clone"
                            clone_reviewer = a.participant
                            # a "clone" predecessor (CP) does not need the review of successor a 
                            clone_pred = a.predecessor
                            # whereas the original predecessor (OP) DOES need such a review...
                            original_pred = a.predecessor.clone_of
                            # ... but OP will have received one if his/her successor (OPS) uploaded
                            original_pred_succ = original_pred.successor
                            # so we check whether OPS exists, but did NOT upload yet
                            # NOTE: and also did NOT reject!!
                            if (original_pred_succ and not original_pred_succ.is_rejected
                                    and original_pred_succ.time_uploaded == DEFAULT_DATE):
                                # if so, we should switch predecessors
                                log_message('Switching predecessors', context['user'])
                                # retrieve the review of the clone, as it must swap its assignment
                                clone_review = PeerReview.objects.filter(
                                    reviewer=clone_reviewer,
                                    assignment=clone_pred
                                    ).first()
                                # NOTE: that the OPS assignment did not upload does NOT mean
                                #       it is not being reviewed, so we get the review-in-progress
                                #       (if any)
                                original_reviewer = original_pred_succ.participant
                                original_review = PeerReview.objects.filter(
                                    reviewer=original_reviewer,
                                    assignment=original_pred
                                    ).first()
                                # HERE WE START THE SWAP:
                                # (1) Give the CP the OPS as successor
                                #     (as OPS did not upload yet).
                                clone_pred.successor = original_pred_succ
                                clone_pred.save()
                                # (2) Also link back, i.e., give the OPS the CP
                                #     as predecessor.
                                original_pred_succ.predecessor = clone_pred
                                original_pred_succ.save()
                                # (3) Make the currently uploaded assignment (a)
                                #     the new successor of the OP.
                                original_pred.successor = a
                                original_pred.save()
                                # (4) Also link a back, i.e., give (a) the OP
                                #     as its predecessor.
                                a.predecessor = original_pred
                                log_message(
                                    'Original now linked to uploader: '
                                        + str(original_pred),
                                    context['user']
                                    )
                                log_message(
                                    'Clone now linked to original successor: '
                                        + str(clone_pred),
                                    context['user']
                                    )
                                # (5) Swap the assignment IDs of the two peer
                                #     review records.
                                clone_review.assignment=original_pred
                                clone_review.save()
                                # NOTE: The original may not be under review
                                #       yet, so we must test.
                                if original_review:
                                    original_review.assignment=clone_pred
                                    original_review.save()
                                # NOTE: User download records must now be
                                #       updated as well, i.e., the OPS student
                                #       now downloaded the CP ...
                                UserDownload.objects.filter(
                                    user=original_pred_succ.participant.student.user,
                                    assignment=original_pred
                                    ).update(assignment=clone_pred)
                                #   ... and the CP student (= current user) now
                                #       downloaded the OP.
                                UserDownload.objects.filter(
                                    user=a.participant.student.user,
                                    assignment=clone_pred
                                    ).update(assignment=original_pred)
                        # Always update a.
                        a.save()
                    # Notify participant of upload success.
                    if a.leg.number > 1:
                        msg = '<br>' + lang.phrase('Predecessor_invited')
                    else:
                        msg = ''
                    if a.on_time_for_bonus():
                        msg += '<br>' + lang.phrase('Half_point_bonus')
                    inform_user(
                        context,
                        lang.phrase('Upload_successful'),
                        lang.phrase('Required_files_received') + msg
                        )
        elif act == 'decline':
            # verify that participant exists
            pid = decode(h, context['user_session'].decoder)
            p = Participant.objects.get(pk=pid)
            if not authorized_participant(p, context['user']):
                raise ValueError('Participant not authenticated')
            lang = p.estafette.course.language
            # see if current assignment can indeed still be declined:
            declined = False
            # get list of all assignments for the student (assigned so far)
            # NOTE: excluding "rejected" assignments!
            a_list = Assignment.objects.filter(participant=p
                ).exclude(is_rejected=True).order_by('-leg__number')
            # the one to be declined = the most recent = the first of the list
            decl_a = a_list.first()
            log_message(
                'TRACE - about to decline assignment: ' + str(decl_a),
                context['user']
                )
            # the assignment cannot be a first step => must have a predecessor
            pred_a = decl_a.predecessor
            if pred_a != None:
                # the predecessor's work must not have been downloaded yet
                if not team_user_downloads(p, [pred_a.id]):
                    # declining is allowed only if the student uploaded work on the same case
                    cases_worked_on = [a.case.id
                        for a in a_list.filter(time_uploaded__gt=DEFAULT_DATE)]
                    if decl_a.case.id in cases_worked_on:
                        # dissociate the assignment from its predecessor
                        pred_a.successor = None
                        pred_a.save()
                        # now the declined assignment can be deleted
                        decl_a.delete()
                        declined = True
                        # NOTE: if the predecessor is the participant, the "selfie" assignment
                        #       can also be deleted
                        if pred_a.is_selfie:
                            pred_a.delete()
            if declined:
                inform_user(context, lang.phrase('You_have_declined'),
                    lang.phrase('Try_again_later'))
            else:
                warn_user(context, lang.phrase('Could_not_decline'),
                    lang.phrase('Downloaded_or_old_URL'))
            # update action status
            p.time_last_action=timezone.now()
            p.save()
        elif act == 'proceed':
            # check whether student is eligible for next assignment
            pid = decode(h, context['user_session'].decoder)
            p = Participant.objects.get(pk=pid)
            if not authorized_participant(p, context['user']):
                raise ValueError('Participant not authenticated')
            p.time_last_action=timezone.now()
            p.save()
            log_message('Proceeding with next step', context['user'])
            # if so, create a new assignment object and set its predecessor
            # NOTE: for clarity, the subsequent operations to achieve this are numbered

            # NOTE: new since September 2019:
            # also consider assigments that HAVE a successor that did NOT submit yet as potential
            # candidates (sort by time elapsed since successor assigned)
            # if choice is between same case or such candidate having a different case,
            # assign a clone!
            
            # get some relay parameters
            p_relay = p.estafette
            p_case_set = p_relay.estafette
            p_template = p_case_set.template
            p_step_count = p_template.nr_of_legs()
            p_case_count = p_case_set.nr_of_cases()

            # (1) get list of all assignments for the student (assigned so far)
            # NOTE: excluding assignments that the student has rejected!
            a_list = team_assignments(p).order_by('-leg__number')
            # (2) get list of legs with a higher number than the latest one
            last_nr = a_list.first().leg.number
            legs = EstafetteLeg.objects.filter(template=p_template
                ).filter(number__gt=last_nr).order_by('number')
            # (3) get the subset of assignments that already have uploads
            u_list = a_list.filter(time_uploaded__gt=DEFAULT_DATE)
            # NOTE: no new assignment unless ALL so far have indeed been uploaded
            #       AND there are still steps to do
            if len(a_list) == len(u_list) and legs:
                # (4) get the next leg and the last submitted assignment
                next_leg = legs.first()  # list was ordered in ascending number order
                last_a = a_list.first()  # list was sorted in descending number order
                # just to be sure, check whether the leg numbers are consecutive
                if last_nr != next_leg.number - 1:
                    raise ValueError('INTERNAL ERROR: steps are not consecutive')
                # (5) get list of CASES the student already worked on
                c_list = [a.case.id for a in a_list]

                # NOTE: multi-threading, so the database transaction must be indivisible
                # NOTE: this still needs implementation with database locking -- TO DO!!
                with transaction.atomic():
                    # (6) find "eligible" assignments for the student to build on
                    # NOTE: we must also filter out the PREDECESSORS of rejected assignments,
                    #       (i.e., the assignments of which the uploaded work was rejected)
                    #       because the elig_set is possibly used later on to identify clone
                    #       candidates
                    rejids = Assignment.objects.filter(participant__estafette=p_relay,
                        leg__number=next_leg.number, is_rejected=True).values_list('predecessor__id')
                    log_message(
                        'TRACE - predecessor IDs of rejected assignments: ' + str(rejids),
                        context['user']
                        )
                    elig_set = Assignment.objects.filter(
                        participant__estafette=p_relay, leg__number=last_nr, is_rejected=False,
                        clone_of__isnull=True, time_uploaded__gt=DEFAULT_DATE
                        ).exclude(id__in=rejids)
                    # elig_set now contains "eligible" predecessors, because:
                    # a) same course-estafette, b) preceding step, c) not rejected (work),
                    # d) not a "clone" of another assignment, and e) uploaded work
                    # NOTE: we exclude "clones" to prevent "cloning clones"
                    log_message(
                        'TRACE - eligible predecessors: '
                            + ', '.join([str(a) for a in elig_set]),
                        context['user']
                        )

                    # (7) ideally, elig_set has a subset of assignments having no successor yet
                    #     and having a case that the student has not worked on yet, but we
                    #     plan for the worst case of neither condition being TRUE
                    no_successor = False
                    new_case = False
                    
                    # start with the complete set of eligible predecessors
                    pr_set = elig_set
                    # narrow it down to those w/o successor and having a new case
                    sub_set = pr_set.filter(successor__isnull=True).exclude(case__in=c_list)
                    log_message(
                        'TRACE - preferred predecessors: '
                            + ', '.join([str(a) for a in sub_set]),
                        context['user']
                        )
                    # if both conditions can be met, the predecessor set can be limited
                    # to this subset
                    if sub_set:
                        pr_set = sub_set
                        no_successor = True
                        new_case = True
                    else:
                        # (8) see if duplicate cases can be avoided by "cloning"
                        sub_set = elig_set.exclude(case__in=c_list)
                        # NOTE: avoid cloning the same assignment twice, as this would
                        #       violate the uniqueness constraint
                        # to effectuate this, get the clones of the subset
                        clone_set = Assignment.objects.filter(clone_of__in=sub_set)
                        # and then remove from the subset the assignments already having a clone
                        sub_set = sub_set.exclude(
                            id__in=clone_set.values_list('clone_of', flat=True))
                        log_message(
                            'TRACE - still clonable predecessors with new case: '
                                + ', '.join([str(a) for a in sub_set]),
                            context['user']
                            )
                        # if so, use this subset of assignments with "new" cases (and successor)
                        if sub_set:
                            pr_set = sub_set
                            new_case = True
                        else:
                            # (9) if duplicate cases cannot be avoided, revert to the eligible
                            #     assignments (regardless of their case) having no successor
                            pr_set = elig_set.filter(successor__isnull=True)
                            log_message(
                                'TRACE - eligible predecessors with known case: '
                                    + ', '.join([str(a) for a in pr_set]),
                                context['user']
                                )
                            if pr_set:
                                no_successor = True
                                # try to exclude the student's own previous step
                                sub_set = pr_set.exclude(participant=p)
                                if sub_set:
                                    pr_set = sub_set

                    # now pr_set is "the best we can do", i.e., in order of preference, either:
                    #  (1) NEW case, NO successor (ideal situation)
                    #  (2) NEW case, a successor, but NO clone
                    #  (3) OLD case, NO successor (3rd choice because different cases are preferred)
                    #  (4) OLD case, a successor, but NO clone
                    # and in all 4 cases, the participant's own work is excluded if possible

                    # NOTE: pr_set cannot be empty because there always should be at least
                    #       one assignment: the previous step of the student;
                    #       even so, we double-check
                    if not pr_set:
                        raise ValueError('No previous assignment found')
                    else:
                        log_message(
                            'TRACE - "best we can do" predecessors: '
                                + ', '.join([str(a) for a in pr_set]),
                                context['user']
                            )
                    
                    # if pr_set contains "free" assignments (case 1 or 3), choose the "best" one
                    if no_successor:
                        # get the case occurrence in the set
                        case_set = pr_set.values('case__id', 'case__letter'
                            ).annotate(c_count=Count('case')
                            ).order_by('-c_count')
                        # print it in readable form
                        ac_str = ', '.join([x['case__letter'] + str(x['c_count']) for x in case_set])
                        log_message('TRACE - case occurrence: ' + ac_str, context['user'])
                        # get the highest count (NOTE: several cases may have this occurrence)
                        high_count = case_set.first()['c_count']
                        # get the case IDs of cases having the highest occurrence
                        high_case_ids = []
                        for x in case_set:
                            if x['c_count'] == high_count:
                                high_case_ids.append(x['case__id'])
                        # (10) select the "best" remaining assignment as predecessor
                        pr_list = list(pr_set.filter(case__in=high_case_ids))
                        pr_list.sort(key=lambda a: -a.participant.progress())
                        # NOTE: the list is ordered in decreasing order of progress
                        #       so that the "fast runners" are preferred over "slow runners"
                        log_message(
                            'TRACE - sorted retained predecessors: '
                                + ', '.join([str(a) for a in pr_list]),
                                context['user']
                                )
                        pr_a = pr_list[0]

                        # NOTE: this predecessor work may be authored by the same participant!
                        if pr_a.participant == p:
                            # if so, it should be cloned as a selfie ...
                            clone, created = Assignment.objects.get_or_create(
                                participant=pr_a.participant,
                                case=pr_a.case, leg=pr_a.leg, time_assigned=pr_a.time_assigned,
                                time_uploaded=pr_a.time_uploaded, clone_of=pr_a,
                                is_selfie=True)
                            if not created:
                                log_message(
                                    'WARNING: attempt to create selfie clone again: '
                                        + str(clone),
                                    context['user']
                                    )
                            # ... and the selfie should be used as predecessor assignment
                            pr_a = clone
                        
                        # (11) create a new assignment that builds on the selected one
                        a, created = Assignment.objects.get_or_create(participant=p,
                            case=pr_a.case, leg=next_leg,
                            predecessor=pr_a)  # other fields have their default value
                        if not created:
                            log_message(
                                'WARNING: attempt to assign step {} again (ID {})'.format(
                                    next_leg.number,
                                    a.id
                                    ),
                                context['user']
                                )
                        # (12) also link the predecessor's assignment to the new one
                        #      (so as to facilitate database lookups later on)
                        pr_a.successor = a
                        pr_a.save()
                        log_message(
                            'Work assigned: ' + str(pr_a),
                            context['user']
                            )
                    else:
                        # if no work without successor can be found, a work needs to be cloned
                        cloning = True
                        log_message(
                            'Looking for suitable clone candidate with new case',
                            context['user']
                            )
                        # NOTE: pr_set now contains predecessors in same course-estafette
                        #       who HAVE been assigned to a successor, are NOT clones,
                        #       and have NOT been cloned yet (cases 2 and 4)

                        # (10b) from this set, we prefer assignments for which the successor
                        # assignment has NOT been uploaded yet, because that may never happen.
                        # NOTE: see the code for the 'upload' action (some 200 lines earlier)
                        #       for explanation on how the successor of a "clone" is re-assigned
                        #       if the successor of its original has not uploaded yet
                        sub_set = pr_set.filter(successor__time_uploaded=DEFAULT_DATE)
                        log_message(
                            'TRACE - predecessors w/o successor having uploaded: '
                                + ', '.join([str(a) for a in sub_set]),
                            context['user']
                            )
                        if sub_set:
                            pr_set = sub_set
    
                        # choose the one having the case with the LOWEST occurrence
                        # (because we're creating a clone)
                        case_set = pr_set.values('case__id', 'case__letter'
                            ).annotate(c_count=Count('case')
                            ).order_by('c_count')  # important! this time NO minus sign
                        # print the choice set
                        ac_str = ', '.join([x['case__letter'] + str(x['c_count'])
                            for x in case_set])
                        log_message('TRACE - clonable case occurrence: ' + ac_str,
                            context['user'])
                        # get the lowest count
                        low_count = case_set.first()['c_count']
                        low_case_ids = []
                        for x in case_set:
                            # retain the IDs of only the low count cases
                            if x['c_count'] == low_count:
                                low_case_ids.append(x['case__id'])
                        # retain only those cases
                        pr_set = pr_set.filter(case__in=low_case_ids)

                        # from this set, select the best remaining assignment as predecessor
                        # NOTE: "best" now means: having the highest grade, since we
                        #       do not want "bad" work to be cloned, as this will
                        #       frustrate/demotivate participants
                        # get reviews on the assignments in the list (if any)
                        rev_set = PeerReview.objects.filter(assignment__in=pr_set
                            ).exclude(grade=0).exclude(is_rejection=True).order_by('-grade')
                        # NOTE: the list is ordered in decreasing order of grade
                        # so that the "good work" is preferred over "bad work"
                        if rev_set:
                            pr_a = rev_set.first().assignment
                        else:
                            pr_a = pr_set.first()
                                    
                        # (11b + 12b) first create a clone of the selected work...
                        clone, created = Assignment.objects.get_or_create(
                            participant=pr_a.participant,
                            case=pr_a.case, leg=pr_a.leg, time_assigned=pr_a.time_assigned,
                            time_uploaded=pr_a.time_uploaded, clone_of=pr_a,
                            # NOTE: set "selfie flag" if we're cloning the student's own work
                            is_selfie=pr_a.participant == p)
                        if not created:
                            log_message(
                                'WARNING: attempt to create clone again: '
                                    + str(clone),
                                context['user']
                                )
                        # ... and make this cloned work the predecessor 
                        a, created = Assignment.objects.get_or_create(participant=p,
                            case=clone.case, leg=next_leg, predecessor=clone)
                        if not created:
                            log_message(
                                'WARNING: attempt to create "build-on-clone" assignment again: '
                                    + str(a),
                                context['user']
                                )
                        clone.successor = a
                        clone.save()
                        log_message(
                            'Clone assigned: ' + str(clone),
                            context['user']
                            )
                        # only inform the student of building on a clone if own work was cloned
                        if clone.is_selfie:
                            lang = p.estafette.course.language
                            inform_user(context, lang.phrase('Frontrunner'),
                                lang.phrase('Continue_own_work'))

                # END OF ATOMIC TRANSACTION

            # if all assignments have been uploaded and no more legs to run...
            elif len(a_list) == len(u_list):
                # (12) check whether how many final steps the student has reviewed
                # first get the last leg of the estafette
                last_leg = EstafetteLeg.objects.filter(template=p_template
                    ).order_by('-number').first()
                fr_list = PeerReview.objects.filter(reviewer=p, assignment__leg=last_leg)
                fr_count = fr_list.filter(time_submitted__gt=DEFAULT_DATE).count()
                # if that number is less than required, create a review
                # NOTE: skip if a final review is still unsubmitted
                #       (this may occur when student refreshes browser)
                if fr_count <= p.estafette.final_reviews and fr_count == len(fr_list):
                    # get list of cases not yet covered by earlier assignments or final reviews
                    cid_list = [a.case.id for a in a_list] + [fr.assignment.case.id for fr in fr_list]
                    new_cases = EstafetteCase.objects.filter(estafette=p_case_set
                        ).exclude(id__in=cid_list)
                    log_message('TRACE: Cases for final review: ' +
                        ', '.join(nc.letter for nc in new_cases), context['user'])
                    # get list of last step assignments with new cases,
                    # starting with the oldest having fewest reviews
                    fra_list = Assignment.objects.filter(
                            participant__estafette=p_relay,
                            leg=last_leg
                        ).exclude(
                            participant=p
                        ).filter(
                            time_uploaded__gt=DEFAULT_DATE,
                            case__id__in=new_cases
                        ).annotate(
                            rev_cnt=Count('peerreview')
                        ).order_by(
                            'rev_cnt',
                            'time_uploaded'
                        ).filter(
                          rev_cnt__lte=p.estafette.final_reviews
                        )
                    # NOTE: last filter ensures that participants do not
                    #       receive more reviews than they should give

                    # PATCH (may be removed / commented out)
                    if (not fra_list): # and (timezone.now() > p.estafette.deadline):
                        # Permit review of cases already worked on
                        fra_list = Assignment.objects.filter(
                            participant__estafette=p.estafette,
                            leg=last_leg
                            ).exclude(participant=p).filter(
                            time_uploaded__gt=DEFAULT_DATE).annotate(
                            rev_cnt=Count('peerreview')).order_by(
                            'rev_cnt',
                            'time_uploaded'
                            ).filter(
                            rev_cnt__lte=p.estafette.final_reviews
                            )
                    # END OF PATCH

                    # guard against creating one too many (may occur when submitting from two browsers)
                    if fra_list and fr_count < p.estafette.final_reviews:
                        rev, created = PeerReview.objects.get_or_create(
                            assignment=fra_list.first(),
                            reviewer=p,
                            final_review_index=fr_count + 1
                            )
                        if not created:
                            log_message(
                                'WARNING: attempt to assign same review again (ID {})'.format(
                                    rev.id
                                    ),
                                context['user']
                                )
                        log_message(
                            'Final review assigned: ' + (str(rev)),
                            context['user']
                            )
                    else:
                        log_message(
                            'Failed to assign final review (no assignments)',
                            context['user']
                            )
                        lang = p_relay.course.language
                        warn_user(context, lang.phrase('Final_review_failed'))
        elif act == 'review':
            # verify that review is indeed for the student's predecessor
            prid = decode(h, context['user_session'].decoder)
            pr = PeerReview.objects.get(pk=prid)
            if not authorized_participant(pr.reviewer, context['user']):
                raise ValueError('Review not authenticated')
            pr.reviewer.time_last_action=timezone.now()
            pr.reviewer.save()
            est = pr.reviewer.estafette
            est_c = est.course
            lang = est_c.language
            # validate the POST parameters
            rat = int(request.POST.get('rat', 0))
            if rat != pr.grade:
                warn_user(
                    context,
                    'Data is inconsistent',
                    '{r} &ne; {g}'.format(r=rat, g=pr.grade),
                    'Rating mismatch: {r} for {u}'.format(r=rat, u=str(pr))
                    )
            # double-check whether review is complete
            elif not pr.is_complete():
                # undo submission (just in case it somehow got beyond this point)
                pr.time_submitted = DEFAULT_DATE
                pr.save()
                warn_user(
                    context,
                    lang.phrase('Review_incomplete'),
                    lang.phrase('Incomplete_peer_review')
                    )
            # check wether review was not submitted already
            elif pr.time_submitted != DEFAULT_DATE:
                warn_user(
                    context,
                    lang.phrase('Review_resubmission'),
                    lang.phrase('Review_submitted_on').format(
                        time=lang.ftime(pr.time_submitted)
                        ),
                    'Review resubmission: ' + str(pr)
                    )
            else:
                sub = request.POST.get('sub', 0)
                # register the review as "submitted" 
                pr.time_submitted = timezone.now()
                pr.save()
                log_message('Review submitted: ' + str(pr), context['user'])
                offense = pr.check_offensiveness()
                if offense:
                    log_message('Language issue: ' + offense, context['user'])

                # if the submit button was not clicked, it must be a rejection
                if rat == 1 and sub == 0:
                    # NOTE: in case of a rejection, several database operations are needed:
                    # (1) the rejected assignment must be "de-assigned" from the reviewer, but
                    # (2) it must keep a successor, or it may be reassigned; therefore
                    # (3) we make the course manager the successor of the rejected assignment
                    with transaction.atomic():
                        pr.is_rejection = True
                        # enroll (if still needed) the course manager
                        cm_s, created = CourseStudent.objects.get_or_create(user=est_c.manager,
                            course=est_c, dummy_index=-1)
                        if created:
                            log_message('Rejecting - created course instructor: '
                                + str(cm_s), context['user'])
                        # create (if needed) the "course manager participant" for this estafette
                        cm_p, created = Participant.objects.get_or_create(student=cm_s,
                            estafette=est)
                        if created:
                            log_message('Rejecting - created instructor participant: '
                                + str(cm_p), context['user'])
                        # get the "rejection bin" assignment for this estafette
                        ec1 = EstafetteCase.objects.filter(estafette=est.estafette).first()
                        el1 = EstafetteLeg.objects.filter(template=est.estafette.template).first()
                        rba, created = Assignment.objects.get_or_create(participant=cm_p,
                            case=ec1, leg=el1)
                        if created:
                            log_message('Rejecting - created "rejection bin" assignment: '
                                + str(cm_p), context['user'])
                        # set the "rejected" flag of the successor's assignment
                        succ_a = pr.assignment.successor
                        succ_a.is_rejected = True
                        succ_a.save()
                        # re-assign the rejected assignment to this "rejection bin" assignment
                        pr.assignment.successor = rba
                        pr.assignment.save()
                        pr.save()
                    log_message(
                        'Rejection succeeded: ' + str(pr),
                        context['user']
                        )
                    msg = (
                        lang.phrase('Predecessor_invited') + '<br>'
                        + lang.phrase('New_predecessor')
                        )
                elif pr.reviewer.student.dummy_index < 0:
                    # instructor review is immediately sent to predecessor; no modification possible
                    msg = lang.phrase('Predecessor_invited')
                else:
                    # no rejection? then modification is possible until successor uploads own work
                    msg = lang.phrase('Can_still_modify')
                inform_user(context, lang.phrase('Review_received'), msg)
        elif act == 'modify':
            # verify the student's assignment parameter
            aid = decode(h, context['user_session'].decoder)
            a = Assignment.objects.get(pk=aid)
            if not authorized_participant(a.participant, context['user']):
                raise ValueError('Assignment not authenticated')
            # register the action
            a.participant.time_last_action=timezone.now()
            a.participant.save()
            lang = a.participant.estafette.course.language
            # verify that the student has a predecessor
            pr_a = a.predecessor
            if not pr_a:
                raise ValueError('Revise failed - predecessor assignment not found')
            # check whether the student indeed reviewed the predecessor's assignment
            rev_set = PeerReview.objects.filter(assignment=pr_a).filter(reviewer=a.participant)
            if not rev_set:                            
                raise ValueError('Revise failed - review not found')
            ok = False
            for rev in rev_set:
                if rev.time_submitted != DEFAULT_DATE and rev.time_appraised == DEFAULT_DATE:
                    # reset the submission time stamp
                    rev.time_submitted = DEFAULT_DATE
                    rev.save()
                    ok = True
            if not ok:                            
                warn_user(context, lang.phrase('Review_can_be_revised'), lang.phrase('Used_old_URL'))
        elif act == 'appraise':
            # verify that appraisal indeed relates to a review of the student's work
            prid = decode(h, context['user_session'].decoder)
            pr = PeerReview.objects.get(pk=prid)
            p = pr.assignment.participant
            if not authorized_participant(p, context['user']):
                raise ValueError('Appraisal not authenticated')
            p.time_last_action=timezone.now()
            p.save()
            lang = p.estafette.course.language
            # check wether appraisal was not submitted already
            if pr.time_appraised != DEFAULT_DATE:
                warn_user(
                    context,
                    lang.phrase('Response_resubmission'),
                    lang.phrase('Response_submitted_on').format(
                        time=lang.ftime(pr.time_appraised)
                        ),
                    'Appraisal resubmission: ' + str(pr)
                    )
            else:
                # NOTE: appraisal data are already saved via AJAX calls
                sub = request.POST.get('sub', 0)
                # double-check that appraisal = 3 if form was submitted with the reject button
                if sub == 0 and pr.appraisal != 3:
                    warn_user(context, 'Appraisal data inconsistent',
                        'Appeal not filed. Please notify the Presto administrator of this error.')
                else:
                    # if the submit button was not clicked, it must be an appeal
                    pr.is_appeal = sub == 0 
                pr.time_appraised = timezone.now()
                pr.save()
                if pr.is_appeal:
                    xtra = '<br>' + lang.phrase('Appeal_filed')
                else:
                    xtra = ''
                inform_user(
                    context,
                    lang.phrase('Response_received'),
                    lang.phrase('Will_see_response') + xtra,
                    'Appraisal submitted: ' + str(pr)
                    )
                # check again for language issues, as appraisals tend to be emotional
                offense = pr.check_offensiveness()
                if offense:
                    log_message('Language issue: ' + offense, context['user'])
        elif act == 'dec-appraise':
            # verify that appraisal indeed concerns an appeal that involves the student
            apid = decode(h, context['user_session'].decoder)
            ap = Appeal.objects.get(pk=apid)
            appraiser = int(request.POST.get('apt', 0))
            if appraiser == 1:  # predecessor
                p = ap.review.assignment.participant
                t = ap.time_acknowledged_by_predecessor
            else:  # successor
                p = ap.review.reviewer
                t = ap.time_acknowledged_by_successor
            if not authorized_participant(p, context['user']):
                raise ValueError('Appeal decision not authenticated')
            # update participant's status
            p.time_last_action=timezone.now()
            p.save()
            lang = p.estafette.course.language
            # check wether appraisal was not submitted already
            if t != DEFAULT_DATE:
                warn_user(
                    context,
                    lang.phrase('Response_resubmission'),
                    lang.phrase('Response_submitted_on').format(time=lang.ftime(t)),
                    'Decision appraisal resubmission: ' + str(ap)
                    )
            else:
                # NOTE: appraisal data are already saved via AJAX calls
                sub = request.POST.get('sub', 0)
                # double-check that appraisal = 3 if form was submitted with the object button
                if appraiser == 1:
                    appr = ap.predecessor_appraisal
                else:
                    appr = ap.successor_appraisal
                # sub can only be zero (not passed) if the objection button was clicked
                if sub == 0 and appr != 3:
                    warn_user(
                        context,
                        'Appraisal data inconsistent',
                        'Objection not filed. Please notify the Presto administrator of this error.'
                        )
                contested = (appr == 3 and sub == 0)
                # update the acknowledgment status of the correct participant (pred or succ)
                if appraiser == 1:
                    ap.is_contested_by_predecessor = contested 
                    ap.time_acknowledged_by_predecessor = timezone.now()
                else:
                    ap.is_contested_by_successor = contested
                    ap.time_acknowledged_by_successor = timezone.now()
                ap.save()
                if contested:
                    xtra = '<br>' + lang.phrase('Objection_filed')
                else:
                    xtra = ''
                inform_user(
                    context,
                    lang.phrase('Response_received'),
                    lang.phrase('Will_see_appraisal') + xtra,
                    'Decision appraisal (by #{}) submitted: '.format(appraiser)
                        + str(ap)
                    )
        elif act == 'acknowledge':
            # verify that appraised review is indeed the student's
            prid = decode(h, context['user_session'].decoder)
            pr = PeerReview.objects.get(pk=prid)
            if not authorized_participant(pr.reviewer, context['user']):
                raise ValueError('Review not authenticated')
            pr.reviewer.last_action=timezone.now()
            pr.reviewer.save()
            lang = pr.reviewer.estafette.course.language
            # check wether appraisal was not already acknowledged
            if pr.time_acknowledged != DEFAULT_DATE:
                warn_user(
                    context,
                    lang.phrase('Appraisal_already_acknowledged'),
                    lang.phrase('Appraisal_acknowledged_on').format(
                        time=lang.ftime(pr.time_acknowledged)
                        ),
                    'Review appraisal re-acknowledgement: ' + str(pr)
                    )
            else:
                pr.time_acknowledged = timezone.now()
                pr.save()
                if pr.is_appeal:
                    xtra = '<br>' + lang.phrase('Predecessor_appealed')
                else:
                    xtra = ''
                inform_user(context, lang.phrase('Appraisal_acknowledged'),
                    lang.phrase('Step_is_history') + xtra)
        elif act == 'referee-appeal':
            # verify that review is indeed a still unassigned appeal
            prid = decode(h, context['user_session'].decoder)
            pr = PeerReview.objects.get(pk=prid)
            lang = pr.reviewer.student.course.language
            if not pr.is_appeal:
                raise ValueError('Review was not appealed against')
            # verify that user is qualified as referee for this appeal
            r = Referee.objects.filter(user=context['user']).filter(estafette_leg=pr.assignment.leg)
            if not r:
                raise ValueError(
                    'Not qualified as referee for step {}'.format(
                        pr.assignment.leg.number
                        )
                    )
            r = r.first()
            if pr.time_appeal_assigned != DEFAULT_DATE:
                ap_list = Appeal.objects.filter(review=pr)
                if ap_list.filter(referee=r):
                    warn = 'You_already_confirmed_to_referee'
                else:
                    warn = 'Assigned_to_other_referee'
                warn_user(context, lang.phrase('Appeal_already_assigned'), lang.phrase(warn))
            else:
                # if authorized, create appeal and update review in a single transaction
                with transaction.atomic():
                    # create an appeal record for this review
                    ap, created = Appeal.objects.get_or_create(referee=r, review=pr)
                    if not created:
                        log_message(
                            'WARNING: attempt to create duplicate appeal (ID {})'.format(
                                ap.id
                            ),
                            context['user']
                            )
                    # set time stamp to indicate that this review-with-appeal has been assigned
                    pr.time_appeal_assigned = timezone.now()
                    pr.save()
                    inform_user(
                        context,
                        lang.phrase('Appeal_assigned'),
                        lang.phrase('You_have_been_appointed')
                        )
        elif act == 'decide' or act == 'decide-objection':
            # differentiate between appeal and objection
            aoid = decode(h, context['user_session'].decoder)
            if act == 'decide':
                ao = Appeal.objects.get(pk=aoid)
                cr = ao.review.reviewer.estafette
                astep = ao.review.assignment.leg.number
                lang = cr.course.language
            else:
                ao = Objection.objects.get(pk=aoid)
                cr = ao.appeal.review.reviewer.estafette
                astep = ao.appeal.review.assignment.leg.number
                lang = cr.course.language
            # verify that decision is indeed the user's
            if ao.referee.user != context['user']:
                raise ValueError('Referee not authenticated')
            # check wether decision was not already pronounced
            if ao.time_decided != DEFAULT_DATE:
                warn_user(
                    context,
                    lang.phrase('Decision_already_pronounced'),
                    lang.phrase('Decision_pronounced_on').format(
                        time=lang.ftime(ao.time_decided)
                        ),
                    'Decision re-submitted: ' + str(ao)
                    )
            else:
                # validate the decision attributes
                wcnt = word_count(ao.grade_motivation)
                if wcnt < cr.minimum_appeal_word_count:
                    raise ValueError(
                        'Referee motivation too short ({} words)'.format(wcnt)
                        )

                # NOTE: temporary solution for 2-grade scoring system
                grade_pair = divmod(ao.grade, 256)
                scsy = cr.scoring_system

                # TEST PATCH!!
                #if ao.id == 1929:
                #    scsy = 2
                #    inform_user(context, 'Set scoring system to 2')

                if (grade_pair[1] < 1 or grade_pair[1] > 5):
                    raise ValueError(
                        'Referee grade ({}) out of range'.format(grade_pair[1])
                        )
                if scsy == 2 and astep > 1 and (grade_pair[0] < 1 or grade_pair[0] > 5):
                    raise ValueError(
                        'Referee grade for predecessor work ({}) out of range'.format(grade_pair[0])
                        )

                pp = round(2 * ao.predecessor_penalty) / 2
                if (pp < -3 or pp > 3):
                    raise ValueError(
                        'Predecessor penalty ({:0.1f}) out of range'.format(pp)
                        )
                sp = round(2 * ao.successor_penalty) / 2
                if (sp < -3 or sp > 3):
                    raise ValueError(
                        'Successor penalty ({:0.1f}) out of range'.format(sp)
                        )
                # if all in order, update the appeal or objection record
                ao.time_decided = timezone.now()
                ao.predecessor_penalty = pp
                ao.successor_penalty = sp
                ao.save()
                inform_user(
                    context,
                    lang.phrase('Decision_pronounced'),
                    lang.phrase('Parties_will_be_informed')
                    )
        elif act == 'referee-objection':
            # verify that appeal is indeed a still unassigned objection
            apid = decode(h, context['user_session'].decoder)
            ap = Appeal.objects.get(pk=apid)
            pr = ap.review
            c = pr.reviewer.student.course
            lang = c.language
            # verify that user is instructor in this course
            if not (c.manager == context['user'] or context['user'] in c.instructors.all()):
                raise ValueError('Not instructor for course ' + str(c))
            # verify that user is qualified as referee for this appeal
            r = Referee.objects.filter(
                user=context['user'],
                estafette_leg=pr.assignment.leg
                )
            if not r:
                raise ValueError(
                    'Not qualified as referee for step {}'.format(
                        pr.assignment.leg.number
                        )
                    )
            r = r.first()
            if not (ap.is_contested_by_predecessor or ap.is_contested_by_successor):
                raise ValueError('Appeal was not objected against')
            if ap.time_objection_assigned != DEFAULT_DATE:
                ob_list = Objection.objects.filter(appeal=ap)
                if ob_list.filter(referee=r):
                    warn = 'You_already_confirmed_to_referee'
                else:
                    warn = 'Assigned_to_other_referee'
                warn_user(context, lang.phrase('Appeal_already_assigned'), lang.phrase(warn))
            else:
                # If authorized, create objection and update appeal
                # in a single transaction.
                with transaction.atomic():
                    # create an objection record for this review
                    ob, created = Objection.objects.get_or_create(
                        referee=r,
                        appeal=ap
                        )
                    if not created:
                        log_message(
                            'WARNING: attempt to create duplicate objection (ID {})'.format(
                                ob.id
                                ),
                            context['user']
                            )
                    # Set time stamp to indicate that this appeal-with-objection
                    # has been assigned.
                    ap.time_objection_assigned = timezone.now()
                    ap.save()
                    inform_user(
                        context,
                        lang.phrase('Objection_assigned'),
                        lang.phrase('You_have_been_appointed')
                        )
        elif act == 'post-review':
            # UGLY HACK: allow argument to have form 1234abc00000 (32 digits)
            # and if the part prior to abc evaluates as an integer, use it as
            # assignment ID
            ugly = h.split('abc')
            if len(ugly) == 2 and ugly[1].replace('0', '') == '':
                aid = int(ugly[0])
            else:
                aid = decode(h, context['user_session'].decoder)
            # Verify that assignment is uploaded.
            a = Assignment.objects.get(pk=aid)
            lang = a.participant.student.course.language
            if a.time_uploaded == DEFAULT_DATE:
                raise ValueError('Assignment was not uploaded')
            # Verify that no instructor review exists for this assignment.
            if PeerReview.objects.filter(assignment=a,
                reviewer__student__dummy_index__lt=0).count() > 0:
                warn_user(context, lang.phrase('Assignment_under_review'))
            else:
                # Verify that user is instructor in the estafette course.
                ip = Participant.objects.filter(
                    student__user=context['user'],
                    estafette=a.participant.estafette,
                    student__dummy_index__lt=0
                    )
                if not ip:
                    raise ValueError('Not instructor for course '
                                     + a.participant.estafette.course.code)
                ip = ip.first()
                # If authorized, make the user (as instructor-participant)
                # reviewer in a single transaction.
                with transaction.atomic():
                    # Create a review record for this assignment.
                    rev, created = PeerReview.objects.get_or_create(
                        assignment=a,
                        reviewer=ip
                        )
                    if not created:
                        log_message(
                            'WARNING: attempt to duplicate instructor review (ID {})'.format(
                                rev.id
                            ),
                            context['user']
                            )
                    inform_user(
                        context,
                        lang.phrase('Post_review_assigned'),
                        lang.phrase('You_can_post_review')
                        )
        elif act != '':
            # Not a valid student action.
            raise ValueError('Invalid student action: ' + act)

    # Catch-all for raised and unanticipated exceptions.
    except Exception as e:
        report_error(context, e) 
        return render(request, 'presto/error.html', context)

    """
    Now all user actions have been processed.
    The following code determines the user's "progress" and produces the
    appropriate view. 
    """
    
    # check whether user is enrolled in any courses
    cl = Course.objects.filter(is_hidden=False,
        coursestudent__user=context['user']).annotate(count=Count('coursestudent'))
    # add this list in readable form to the context (showing multiple enrollments)
    context['course_list'] = ',&nbsp;&nbsp; '.join([
        c.title()
            + (' <span style="font-weight: 800; color: red">{}&times;</span>'.format(
                c.count) if c.count > 1 else ''
              )
        for c in cl
        ])

    # maintain a list of course languages to minimize the number of modals needed
    context['languages'] = []
    l_codes = []
    for c in cl:
        lang = c.language
        if not lang.code in l_codes:
            l_codes.append(lang.code)
            context['languages'].append(lang)

    # add "nothing to do" phrase to overall page context
    if cl:
        lang = cl.first().language
    else:
        lang = Language.objects.first()
    context['No_tasks_to_do'] = lang.phrase('No_tasks_to_do')

    # student (but also instructor in that role) may be enrolled in several courses
    # NOTE: "instructor students" (dummy_index < 0) are included so that they can do reviews
    csl = CourseStudent.objects.filter(user=context['user'])

    # get the visible estafettes for all the student's courses (even if they are not active)
    cel = CourseEstafette.objects.filter(is_deleted=False, is_hidden=False,
        course__in=[cs.course.id for cs in csl])

    # add this list in readable form to the context
    context['estafette_list'] = ',&nbsp;&nbsp; '.join([ce.title() for ce in cel])

    # limit the set to the "active" estafettes
    acel = cel.exclude(start_time__gte=timezone.now()
                        ).exclude(end_time__lte=timezone.now())
    
    # get the set of all the course student's current participations
    # so as to avoid duplicate "enrollment" in the same course estafette
    pl = Participant.objects.filter(student__in=[cs.id for cs in csl])
    
    # make student participant in all active course estafettes, unless already
    for ace in acel:
        for cs in csl:
            if ace.course == cs.course and not pl.filter(student=cs).filter(estafette=ace):
                p = Participant(student=cs, estafette=ace)
                p.save()
                # add "instructor participant" without notification, as they
                # do not really participate
                if cs.dummy_index >= 0:
                    inform_user(
                        context, lang.phrase('Joined_relay'),
                        lang.phrase('You_just_joined').format(
                            relay=p.estafette.title()
                            ),
                        'New participant: ' + str(p)
                        )

    # NOTE: when impersonating a user, instructor users should NOT be seen as instructor
    in_instructor_role = (context['user'] == context['user_session'].user) and has_role(context, 'Instructor')

    # get all the student's participant objects -- now including those just added
    # but excluding hidden and finished estafettes, as these should appear only in the History
    # NOTE: for instructors, show relays until 90 days after closing date
    t_now = timezone.now()
    if in_instructor_role:
        final_dt = t_now - timedelta(days=MAX_DAYS_BEYOND_END_DATE)
    else:
        final_dt = t_now
    # NOTE: for "instructor students", the finished estafettes should NOT be excluded!
    opl = Participant.objects.filter(
        estafette__is_deleted=False, estafette__is_hidden=False, student__in=[cs.id for cs in csl]
        ).exclude(estafette__start_time__gte=t_now
        ).exclude(estafette__end_time__lte=final_dt
        ).distinct().select_related('estafette', 'estafette__course')
    
    # if user is a "focused" dummy user (i.e., has an alias), retain only this course user's participations
    if 'alias' in context:
        opl = pl.filter(student=context['csid'])
    
    # replace participant by its team leader if applicable
    # NOTE: do NOT switch to team leader if p has not started yet
    pl = []
    for p in opl:
        if p.time_started == DEFAULT_DATE:
            pl.append(p)
        else:
            ctl = current_team_leader(p)
            pl.append(ctl if ctl else p)

    # for the introduction video, the step and star index are both 0
    context['intro_video'] = LegVideo.objects.filter(leg_number = 0, star_range = 0).first()
    # determine what other video clips are needed (if any)
    videos = {}
    video_languages = []
    for p in pl:
        if not p.estafette.course.language in video_languages:
            video_languages.append(p.estafette.course.language)
            videos[p.estafette.course.language.code] = [{1: None, 2: None} for i in range(7)]  
            # NOTE: for each language 2x6 clips in a [step, stars] matrix;
            #       step index 5 is for the penultimate step, step index 6 for the last step
    for v in LegVideo.objects.filter(language__in=video_languages, leg_number__gt=0, star_range__gt=0):
        videos[v.language.code][v.leg_number][v.star_range] = v

    # start with an empty list (0 participations)
    context['participations'] = []
    p_nr = 0
    # for each participation, create a context entry with tasks
    for p in pl:
        # number participations to be able to identify elements in JavaScripts
        p_nr += 1
        # likewise number tasks within each participation
        t_nr = 0
        # estafettes "speak" the language of their course
        lang = p.estafette.course.language
        ce = p.estafette
        past_deadline = extended_assignment_deadline(p) < timezone.now()
        past_review_deadline = extended_review_deadline(p) < timezone.now()
        # see if participant is referee in this relay
        rcnt = Referee.objects.filter(
            user=context['user'],
            estafette_leg__template=ce.estafette.template
            ).count()
        part = {
            'object': p,
            'team': team_as_html(p),
            'nr': p_nr,
            'start': lang.ftime(ce.start_time),
            'end': lang.ftime(ce.end_time),
            'next_deadline': ce.next_deadline(),
            'desc': ce.estafette.description,
            'steps': ce.estafette.template.nr_of_legs(),
            'hex': encode(p.id, context['user_session'].encoder),
            'can_focus': p.student.dummy_index > 0,
            'is_referee': lang.phrase('You_are_referee').format(
                n=(rcnt if rcnt else '')
                ),
            'suspended': ce.suspended(),
            'tasks': [],
            # NOTE: relays in different courses may have different languages
            'lang': lang,
            'past_deadline': past_deadline,
            'past_review_deadline': past_review_deadline
            }
        
        # TO DO: add "question prompt" as field to CourseEstafette model
        # for now, set it to TRUE for TB112 courses only
        # NOTE: use %% instead of double quotes because strings are passed as
        # JavaScript function parameters!!
        if ce.course.code[:5] == 'TB112' and not ce.suspended():
            # and context['user_session'].user.username == 'pbots':
            part['q_header'] = 'Stel je vraag aan de docent'
            part['q_prompt'] = ' '.join([
                '<p>Ga eerst na of je het antwoord op je vraag niet al',
                '<a href=%%https://sysmod.tbm.tudelft.nl/wiki/index.php/ModEst:FAQ_lopende_estafette%%',
                'target=%%_blank%%><strong>op de FAQ voor de ModelleerEstafette</strong></a> kunt vinden!</p>',
                '<p>Is dat echt niet het geval, formuleer je vraag dan hieronder en klik op',
                '<strong>Versturen</strong>.</p>'
                ])
            part['q_submit'] = 'Versturen'
            part['q_cancel'] = 'Annuleren'

        # show "defocus" button if focused, but NOT for demonstration users
        if 'alias' in context and not is_demo_user(context):
            part['can_defocus'] = True

        # NOTE: exclude "instructor students" (dummy index < 0) from all actions except review!

        # if the student still needs to accept the "rules of the game", this always comes first
        if (p.student.dummy_index >= 0
            and not (past_deadline or p.time_started > DEFAULT_DATE)
            # NOTE: participant should not be prompted to accept rules
            #       for another user (notably: his/her team leader)
            and p.student.user == context['user']):
            part['rules'] = lang.phrase('Rules_of_the_game')
            if part['team']:
                part['rules'] += lang.phrase('Team_rules')
        else:
            # add participant's progress data to the context
            part['things_to_do'] = things_to_do(p)
            # get list of all assignments for the participant (or team leader) assigned so far
            a_list = team_assignments(p).order_by('-leg__number')
            # get subset that already have uploads -- these may need review appraisal
            u_list = a_list.filter(time_uploaded__gt=DEFAULT_DATE)
            # remember the case IDs of the uploaded assignments (used to establish decline option)
            cases_worked_on = [u.case.id for u in u_list]

            # get assigned final reviews that still need to be sumbitted (if any)
            final_reviews = PeerReview.objects.filter(reviewer=p,
                assignment__leg__number=part['steps']).exclude(time_submitted__gt=DEFAULT_DATE)

            # get pending instructor reviews (if any; only for "instructor participants")
            if p.student.dummy_index < 0:
                instructor_reviews = PeerReview.objects.filter(reviewer=p,
                    ).exclude(time_submitted__gt=DEFAULT_DATE)
            else:
                instructor_reviews = []
            log_message('IR: ' + str(instructor_reviews) + ' - ' + str(p.student), p.student.user)
            # if a_list has more elements than u_list, the student still has a pending assignment
            unfinished_step = len(a_list) > len(u_list)

            # s/he then must upload the pending assignment, and cannot ask for the next step
            # NOTE: also follow this thread when final reviews have been assigned, and also
            #       when user is "instructor participant" and has instructor reviews to do
            if ((unfinished_step and not past_deadline)
                or (final_reviews and not past_review_deadline)) or instructor_reviews:
                # "instructor participants" typically do not have any assignments,
                # except for the "rejection bin" assignment (one per relay) that is used
                # as "dummy successor" for assignments with rejected work
                rev = None                
                if len(instructor_reviews) > 0: # not a_list:
                    log_message('Selecting first instructor review')
                    a = None
                    rev = instructor_reviews.first()
                    pr_a = rev.assignment                
                else:
                    a = a_list.first()
                    if final_reviews:
                        rev = final_reviews.first()
                        pr_a = rev.assignment
                    else:
                        pr_a = a.predecessor
                        
                # NOTE: rev is NOT defined when a "regular" assignment review is concerned

                # check whether the student already downloaded the predecessor's work
                aids = [pr_a.id] if pr_a else []
                pr_download = team_user_downloads(p, aids).first()

                # if assignment is a first step, then uploading is the only option
                # (but NOT for "instructor students")
                if unfinished_step and p.student.dummy_index >= 0 and a and a.leg.number == 1:
                    fl = a.leg.file_list()
                    t_nr += 1
                    # calculate time since user started with this assignment
                    min_since_start = int((timezone.now() -
                        a.time_assigned).total_seconds() / 60) + 1
                    min_to_wait = int(a.leg.min_upload_minutes) - min_since_start + 1
                    # see whether half star bonus is (still) attainable
                    bonus = a.on_time_for_bonus(min_to_wait)
                    if bonus:
                        bonus = lang.phrase('Steady_pace_bonus').format(time=bonus)  
                    part['tasks'].append({
                        'nr': t_nr,
                        'type': 'UPLOAD',
                        'task': lang.phrase('Upload'),
                        'header': lang.phrase('Upload_header').format(
                            nr=a.leg.number,
                            name=a.leg.name
                            ),
                        'case_letter': a.case.letter,
                        'case_title': a.case.title(lang.phrase('Case')),
                        'case': ui_img(a.case.description),
                        'desc': a.leg.description,
                        'instr': a.leg.upload_instruction,
                        'rev_instr': a.leg.complete_review_instruction(),
                        # get assignment items (if any)
                        'upl_items': a.item_list(),
                        'file_list': fl,
                        'min_to_wait': min_to_wait + 1,  # add 1 to compensate for rounding down
                        'bonus': bonus,
                        # characteristic icon and color for this task
                        'icon': 'upload',
                        'color': 'purple',
                        'hex': encode(a.id, context['user_session'].encoder),
                    })
                    # pass hex for case if it has a file attached
                    if a.case.upload:
                        part['tasks'][-1]['case_hex'] = encode(
                            a.case.id,
                            context['user_session'].encoder
                            )

                elif not pr_a:
                    log_message(
                        'NOTICE: Not showing "rejection bin" assignment ' + str(a),
                        context['user']
                        )
                # if student has not yet looked at predecessor's work, that's the next task
                # NOTE: this only applies to steps with required files
                elif (pr_download is None and a and a.leg.required_files
                        and not (past_review_deadline or instructor_reviews)):
                    t_nr += 1
                    too_late = ''
                    # no bonus teaser for final reviews
                    if final_reviews:
                        bonus = ''
                    else:
                        # see whether half star bonus is (still) attainable
                        bonus = a.on_time_for_bonus()
                        if bonus:
                            bonus = lang.phrase('Steady_pace_bonus').format(time=bonus)
                        # warn participants if they're too late to finish an assignment
                        ead = extended_assignment_deadline(p)
                        if timezone.now() + timedelta(minutes=a.leg.min_upload_minutes) > ead:
                            too_late = lang.phrase('Too_late_to_complete').format(
                                min=a.leg.min_upload_minutes
                                )
                        else:
                            ml = int((ead - timezone.now()).total_seconds() / 60)
                            log_message(
                                'Still {m} minutes until deadline'.format(m=ml),
                                context['user']
                                )
                    part['tasks'].append({
                        'nr': t_nr,
                        'type': 'DOWNLOAD',
                        'task': lang.phrase('Download'),
                        'header': lang.phrase(
                            'Final_download_header' if final_reviews else 'Download_header'
                           ).format(nr=pr_a.leg.number, name=pr_a.leg.name),
                        'case_letter': pr_a.case.letter,
                        'case_title': pr_a.case.title(lang.phrase('Case')),
                        'case': ui_img(pr_a.case.description),
                        'desc': pr_a.leg.description,
                        'file_list': pr_a.leg.file_list(),
                        'bonus': bonus,
                        'did_download': len(team_user_downloads(p, [pr_a.id])) > 0,
                        'may_decline': not final_reviews and (a.case.id in cases_worked_on),
                        'selfie': pr_a.participant == p,
                        'too_late': too_late,
                        # characteristic icon and color for this task
                        'icon': 'download',
                        'color': 'blue',
                        'hex': encode(pr_a.id, context['user_session'].encoder)
                        # hex passes ID of assignment that can be downloaded 
                        # the successor can be inferred from this assignment 
                    })
                    # pass hex for case if it has a file attached
                    if a.case.upload:
                        part['tasks'][-1]['case_hex'] = encode(a.case.id, context['user_session'].encoder)

                # not a first step and predecessor's work has been viewed => show review form
                else:
                    # by default, no bonus teaser (should be shown only for regular reviews)
                    bonus = ''

                    if instructor_reviews:
                        # ensure that instructors do not have a minimum review time
                        min_to_wait = -1
                    else:
                        # calculate minutes since the work has been downloaded
                        # NOTE: if no work was downloaded, use the time the step was assigned
                        if pr_download:
                            t = pr_download.time_downloaded
                        else:
                            t = a.time_assigned
                        min_since_download = int((timezone.now() - t).total_seconds() / 60) + 1
                        min_to_wait = int(a.leg.min_upload_minutes) - min_since_download + 1
                        if not final_reviews:
                            # see whether half star bonus is (still) attainable
                            bonus = a.on_time_for_bonus(min_to_wait)
                            if bonus:
                                bonus = lang.phrase('Steady_pace_bonus').format(time=bonus)  

                    # student must first (or still) review a predecessor
                    if not (final_reviews or instructor_reviews):
                        rev, created = PeerReview.objects.get_or_create(
                            assignment=pr_a,
                            reviewer=p
                            )
                        if created:
                            log_message(
                                ''.join([
                                    'Review assigned to ',
                                    p.student.dummy_name(),
                                    ': assignment',
                                    str(a)
                                    ]),
                                context['user']
                                )
                    # check whether review has been done
                    if rev and rev.time_submitted == DEFAULT_DATE:
                        # if not, this task must be done first
                        if instructor_reviews:
                            r_header = 'Instructor_review_header'
                            r_icon = 'student'
                            minwords = 10
                        elif final_reviews:
                            r_header = 'Final_review_header'
                            r_icon = 'star'
                            minwords = pr_a.leg.word_count
                        else:
                            r_header = 'Review_header'
                            r_icon = 'star outline'
                            minwords = pr_a.leg.word_count
                        t_nr += 1
                        part['tasks'].append({
                            'nr': t_nr,
                            'type': 'REVIEW',
                            'task': lang.phrase('Review'),
                            'header': lang.phrase(r_header).format(
                                nr=pr_a.leg.number,
                                name=pr_a.leg.name
                                ),
                            'case_letter': pr_a.case.letter,
                            'case_title': pr_a.case.title(lang.phrase('Case')),
                            'case': ui_img(pr_a.case.description),
                            'desc': pr_a.leg.description,
                            'rev_inst': ui_img(pr_a.leg.review_instruction),
                            'min_words': minwords,
                            'selfie': pr_a.is_selfie,
                            'rejectable': pr_a.leg.rejectable,
                            # also add assignment items (if any)
                            'upl_items': pr_a.item_list(),
                            'file_list': pr_a.leg.file_list(),
                            'grade': rev.grade,
                            'reject': rev.is_rejection,
                            # get item reviews
                            'rev_items': rev.item_list(),
                            'rev': rev.grade_motivation,
                            'rev_words': word_count(rev.grade_motivation),
                            # pass review model text (if any) as plain text
                            # NOTE: this feature has been deprecated!!
                            'rev_model': pr_a.leg.review_model_text,
                            # NOTE: also show the bonus teaser in the review section
                            'bonus': bonus,
                            # characteristic icon and color for this task
                            'icon': r_icon,
                            'color': 'orange',
                            # here, too, hex passes ID of assignment that can be downloaded ...
                            'hex': encode(pr_a.id, context['user_session'].encoder),
                            # ... but we also pass the ID of the review object for this assignment
                            'rev_hex': encode(rev.id, context['user_session'].encoder),
                        })
                        # pass hex for case if it has a file attached
                        if pr_a.case.upload:
                            part['tasks'][-1]['case_hex'] = encode(
                                pr_a.case.id, context['user_session'].encoder)
                    elif not final_reviews:
                        # if review HAS been done (and was not a final review),
                        # the student should upload own assignment
                        t_nr += 1
                        part['tasks'].append({
                            'nr': t_nr,
                            'type': 'UPLOAD',
                            'task': lang.phrase('Upload'),
                            'header': lang.phrase('Upload_header').format(
                                nr=a.leg.number,
                                name=a.leg.name
                                ),
                            'case_letter': a.case.letter,
                            'case_title': a.case.title(lang.phrase('Case')),
                            'case': a.case.description.replace(
                                '<img ',
                                '<img class="ui large image" '
                                ),
                            'desc': a.leg.description,
                            'instr': a.leg.upload_instruction,
                            'rev_instr': a.leg.complete_review_instruction(),
                            'file_list': a.leg.file_list(),
                             # add 1 minute to compensate for rounding down
                            'min_to_wait': min_to_wait + 1,
                            'bonus': bonus,
                            'can_revise': True,
                            # characteristic icon and color for this task
                            'icon': 'upload',
                            'color': 'purple',
                            'hex': encode(a.id, context['user_session'].encoder),
                        })
                        # pass hex for case if it has a file attached
                        if a.case.upload:
                            part['tasks'][-1]['case_hex'] = encode(a.case.id, context['user_session'].encoder)

            # if neither of these, then look whether there still is a next step
            # (but NOT for "instructor students")
            if p.student.dummy_index >= 0 and not part['tasks']:
                # get list of steps not yet covered by these assignments
                new_steps = EstafetteLeg.objects.filter(template=p.estafette.estafette.template
                    ).exclude(id__in=[a.leg.id for a in a_list])
                if new_steps and not past_deadline:
                    # if yes, then student should be prompted to go to the next step
                    n = new_steps.count()
                    if n == 1:
                        steps_to_go = lang.phrase('One_more_step')
                    else:
                        steps_to_go = lang.phrase('Steps_ahead').format(nr=n)
                    leg = new_steps.first()
                    # warn participants if they're too late to finish an assignment
                    ead = extended_assignment_deadline(p)
                    if timezone.now() + timedelta(minutes=leg.min_upload_minutes) > ead:
                        too_late = lang.phrase('Too_late_to_complete').format(
                            min=leg.min_upload_minutes
                            )
                    else:
                        ml = int((ead - timezone.now()).total_seconds() / 60)
                        log_message(
                            'Still {} minutes until deadline'.format(ml),
                            context['user']
                            )
                        too_late = ''
                    t_nr += 1
                    part['tasks'].append({
                        'nr': t_nr,
                        'type': 'PROCEED',
                        'task': lang.phrase('Proceed'),
                        'header': lang.phrase('Proceed_header').format(
                            nr=leg.number,
                            name=leg.name
                            ),
                        'desc': '',  # no description of the next assignment (yet)
                        'your_task': steps_to_go,
                        'too_late': too_late,
                        # characteristic icon and color for this task
                        'icon': 'arrow circle right',
                        'color': 'olive'
                        })
                elif not (new_steps or unfinished_step):
                    # if not, check whether how many final steps the student has reviewed
                    fr_list = PeerReview.objects.filter(reviewer=p, assignment__leg__number=part['steps'])
                    fr_count = fr_list.filter(time_submitted__gt=DEFAULT_DATE).count()
                    # if that number is less than required, prompt student to ask for a review
                    fr_to_do = p.estafette.final_reviews - fr_count
                    if fr_to_do > 0 and not past_review_deadline:
                        # get list of cases not yet covered by earlier assignments or final reviews
                        cid_list = [a.case.id for a in a_list] + [fr.assignment.case.id for fr in fr_list]
                        # print('CIDs: ' + ', '.join(str(x) for x in cid_list))
                        new_cases = EstafetteCase.objects.filter(
                            estafette=p.estafette.estafette).exclude(id__in=cid_list)
                        log_message('New cases: ' + ', '.join(nc.letter for nc in new_cases), context['user'])
                        # get list of submitted (!) last step assignments having new cases,
                        # starting with the oldest having fewest reviews
                        fra_list = Assignment.objects.filter(
                            participant__estafette=p.estafette,
                            leg__number=part['steps']
                            ).exclude(participant=p).filter(
                            time_uploaded__gt=DEFAULT_DATE).filter(
                            case__id__in=new_cases).annotate(
                            rev_cnt=Count('peerreview')).order_by(
                            'rev_cnt',
                            'time_uploaded'
                            ).filter(
                            rev_cnt__lte=p.estafette.final_reviews
                            )

                        # PATCH (may be removed / commented out)
                        if (not fra_list): # and (timezone.now() > p.estafette.deadline):
                            # Permit review of cases already worked on
                            fra_list = Assignment.objects.filter(
                                participant__estafette=p.estafette,
                                leg__number=part['steps']
                                ).exclude(participant=p).filter(
                                time_uploaded__gt=DEFAULT_DATE).annotate(
                                rev_cnt=Count('peerreview')).order_by(
                                'rev_cnt',
                                'time_uploaded'
                                ).filter(
                                rev_cnt__lte=p.estafette.final_reviews
                                )

                        # always tell student how many reviews still need to be done
                        if fr_to_do == 1:
                            part['final_reviews_to_do'] = lang.phrase(
                                'One_final_review'
                                )
                        else:
                            part['final_reviews_to_do'] = lang.phrase(
                                'Several_final_reviews'
                                ).format(n=fr_to_do)
                        # if available, ask student to proceed
                        # NOTE: since Nov 2021 option to defer final reviews to
                        # AFTER the assignment deadline
                        if (p.estafette.final_reviews_at_end()
                            and timezone.now() < p.estafette.deadline):
                            # Inform student that s/he has to wait
                            part['no_final_reviews'] = lang.phrase(
                                'Final_reviews_after_step'
                                )                            
                            part['explain_final_reviews'] = lang.phrase(
                                'Explain_final_reviews_after_step'
                                )          
                        elif fra_list:
                            log_message(
                                '{} final review candidates'.format(len(fra_list)),
                                context['user']
                                )
                            # Do not assign, but let student click on "Proceed"
                            # to obtain a new review
                            # NOTE: The Final_reviews context entry serves as
                            #       "flag" in the template.
                            part['Final_reviews'] = part['final_reviews_to_do']
                        else:
                            # Inform student that s/he has to wait.
                            part['no_final_reviews'] = lang.phrase(
                                'No_final_reviews'
                                )
                    elif fr_to_do > 0:
                        # NOTE: The Past_deadline context entry serves as "flag"
                        #       in the template!
                        part['Past_deadline'] = lang.phrase('Past_review_deadline')
                    elif p.estafette.end_time > timezone.now():
                        # if all is done, display "finish" until the estafette end time
                        # NOTE: the Finished context entry serves as flag in the template!
                        part['Finished'] = lang.phrase('Finished')
                elif not instructor_reviews:
                    # NOTE: the Past_deadline context entry serves as flag in the template!
                    part['Past_deadline'] = lang.phrase('Past_deadline')

            # At all times, the student may need to repond to reviews of
            # his/her own work. Such reviews must be submitted AND the successor
            # must have uploaded the next step AND the assignment should not be
            # a clone (NOTE: owned by the student him/herself)
            pr_list = PeerReview.objects.filter(
                    assignment__participant=p
                ).exclude(
                    time_submitted=DEFAULT_DATE
                ).filter(
                    time_appraised=DEFAULT_DATE
                ).exclude(
                    Q(assignment__successor__time_uploaded=DEFAULT_DATE)
                        & Q(is_rejection=False)
                ).exclude(
                    assignment__clone_of__isnull=False
                )
            for pr in pr_list:
                a = pr.assignment
                own_fl = a.leg.file_list()
                # NOTE: Final reviews and instructor reviews have no
                #       successor assignment!
                if a.successor == None or pr.reviewer.student.dummy_index < 0:
                    suc_fl = []
                else:
                    suc_fl = a.successor.leg.file_list()
                # Modify task title so the student knows s/he is looking at
                # earlier work
                part['peer_review'] = True
                t_nr += 1
                part['tasks'].append({
                    'nr': t_nr,
                    'type': 'APPR-REV',
                    'task': lang.phrase('Respond'),
                    'header': lang.phrase('Respond_header').format(
                        nr=a.leg.number,
                        name=a.leg.name
                        ),
                    'case_title': a.case.title(lang.phrase('Case')),
                    'case': ui_img(a.case.description),
                    'desc': a.leg.description,
                    'peer_review': pr,
                    'rev_items': pr.item_list(),
                    # NOTE: task now refers to former task!
                    'your_task': lang.phrase('Your_task_was'),
                    # characteristic icon and color for this task
                    'icon': 'comments outline',
                    'color': 'violet',
                    'hex': encode(pr.id, context['user_session'].encoder),
                    'own_hex': encode(pr.assignment.id, context['user_session'].encoder),
                    'own_file_list': own_fl,
                    'appr_words': word_count(pr.appraisal_comment)
                })
                # pass hex for case if it has a file attached
                if a.case.upload:
                    part['tasks'][-1]['case_hex'] = encode(a.case.id, context['user_session'].encoder)
                # add successor file list only for assignments having a successor 
                if a.successor:
                    part['tasks'][-1].update({
                        'suc_hex': encode(a.successor.id, context['user_session'].encoder),
                        'suc_file_list': suc_fl
                    })
                # add video clip if this option has been set
                if p.estafette.with_review_clips:
                    step_index = 0
                    if a.leg.number == part['steps']:
                        step_index = 6
                    elif a.leg.number == part['steps'] - 1:
                        step_index = 5
                    elif a.leg.number <= 4:
                        step_index = a.leg.number
                    # no clips for steps 5, ..., N - 2 if estafette has more than 6 steps
                    if step_index:
                        part['tasks'][-1].update({
                            'video_clip': videos[lang.code][step_index][1 if pr.grade < 3 else 2]
                        })

            # ALSO at all times, the student may need to acknowledge appraisals of his/her reviews
            # provided that such appraisals have been submitted and not already acknowledged
            pr_list = PeerReview.objects.filter(reviewer=p
                ).exclude(time_appraised=DEFAULT_DATE).filter(time_acknowledged=DEFAULT_DATE)
            for pr in pr_list:
                t_nr += 1
                a = pr.assignment
                part['appraised_review'] = True
                part['tasks'].append({
                    'nr': t_nr,
                    'type': 'ACK-APPR',
                    'task': lang.phrase('Acknowledge'),
                    'header': lang.phrase('Acknowledge_header').format(
                        nr=a.leg.number,
                        name=a.leg.name
                        ),
                    'case_title': a.case.title(lang.phrase('Case')),
                    'case': lang.phrase('Details_in_history'),
                    'desc': '',
                    'appraised_review': pr,
                    'is_final': a.leg.number == part['steps'],
                    'rev_items': pr.item_list(),
                    'your_task': lang.phrase('Please_confirm_read'),
                    'app_icon': FACES[pr.appraisal],
                    'app_header': lang.phrase(
                        'Appraisal_header').format(
                            opinion=lang.phrase(OPINIONS[pr.appraisal])
                            ),
                    'imp_opinion': ''.join([
                        lang.phrase('Opinion_on_sucessor_version'),
                        ' &nbsp;<tt>',
                        lang.phrase(
                            ['Pass', 'No_improvement', 'Minor_changes',
                             'Good_job'][pr.improvement_appraisal]
                            ),
                        '</tt>'
                        ]),
                    # characteristic icon and color for this task
                    'icon': 'check circle outline',
                    'color': 'pink',
                    'hex': encode(pr.id, context['user_session'].encoder)
                })
            
            # ALSO at all times, the student may need to appraise a referee decision on appeal cases
            # in which s/he is a party, provided that such appeals have been decided upon,
            # and NOT already been acknowledged (hence second parameter not_ack=True)
            ap_list = team_appeals(p, True)
            for ap in ap_list:
                t_nr += 1
                part['decided_appeal'] =  True
                a = ap.review.assignment
                lang = a.participant.student.course.language
                # NOTE: grade encodes TWO star scores
                grade_pair = divmod(ap.grade, 256)
                # some task properties differ between predecessor and successor
                if a.participant == p:
                    appraiser = 1 # appraiser type number used later in ajax.py
                    dec_appr = ap.predecessor_appraisal
                    appr_motiv = ap.predecessor_motivation
                    xtra = ' (' + lang.phrase('As_predecessor') + ')'
                else:
                    appraiser = 2 # appraiser type number used later in ajax.py
                    dec_appr = ap.successor_appraisal
                    appr_motiv = ap.successor_motivation
                    xtra = ' (' + lang.phrase('As_successor') + ')'
                # disable objection when appeal has been decided by an instructor
                if a.participant.estafette.course.instructors.filter(pk=ap.referee.user.pk):
                    may_object = False
                    possibility_to_object = lang.phrase('Refereed_by_instructor')
                    objection_hint = lang.phrase('No_objection_possible')
                else:
                    may_object = True
                    possibility_to_object = lang.phrase('Object_if_unfair')
                    objection_hint = lang.phrase('Objection_rule')
                # set task properties
                part['tasks'].append({
                    'nr': t_nr,
                    'type': 'APPR-DEC',
                    'task': lang.phrase('Appraise_appeal_decision'),
                    'header': lang.phrase('Appraise_appeal_header').format(
                        nr=a.leg.number,
                        name=a.leg.name
                        ),
                    'case_title': a.case.title(lang.phrase('Case')),
                    'case': lang.phrase('Appeal_review_in_history'),
                    'desc': '',
                    'decided_appeal': ap,
                    'scoring_system': a.participant.estafette.scoring_system,
                    'grade': grade_pair[1],
                    'prior_grade': grade_pair[0],
                    'time_appealed': lang.ftime(ap.review.time_appraised),
                    'time_assigned': lang.ftime(ap.review.time_appeal_assigned),
                    'time_decided': lang.ftime(ap.time_decided),
                    'penalty_text': lang.penalties_as_text(ap.predecessor_penalty, ap.successor_penalty),
                    'your_task': lang.phrase('Appraise_appeal_decision') + xtra,
                    'appraiser': appraiser,
                    'dec_appr': dec_appr,
                    'appr_motiv': appr_motiv,
                    'appr_words': word_count(appr_motiv),
                    'may_object': may_object,
                    'possibility_to_object': possibility_to_object,
                    'objection_hint': objection_hint,
                    # characteristic icon and color for this task
                    'icon': 'law',
                    'color': 'grey',
                    'hex': encode(ap.id, context['user_session'].encoder)
                })
                # only display time first viewed if such viewing occurred
                if ap.time_first_viewed != DEFAULT_DATE:
                    part['tasks'][-1]['time_viewed'] = lang.ftime(ap.time_first_viewed)
            
            # STILL TO DO: the student may be willing to give a "second opinion"
            
        # store this specific student data for this estafette in the context
        context['participations'].append(part)

    # END of FOR-loop back over all participations)

    # MOREOVER, instructors may have to decide on objections and appeals
    ob = None
    ap = None
    # NOTE: instructors should not be allowed to take on more than 1 such case at a time
    # so first get the list of the user's "undecided" objections (if any)
    ob_list = Objection.objects.filter(referee__user=context['user']).filter(time_decided=DEFAULT_DATE)
    if ob_list:
        # add data on the undecided objection to the context
        ob = ob_list.first()
        ap = ob.appeal
    else:
        # no objection case? then check whether the user has a still undecided appeal case
        ap_list = Appeal.objects.filter(referee__user=context['user']).filter(time_decided=DEFAULT_DATE)
        if ap_list:
            ap = ap_list.first()
    # since objection cases include all data related to appeal cases, treat them largely as similar
    if ob or ap:
        ar = ap.review
        a = ar.assignment
        e = a.participant.estafette
        lang = e.course.language
        scsy = e.scoring_system
        ob_or_ap = ob if ob else ap
        prior_rev_inst = ''

        # TEST PATCH!!
        #if ob_or_ap.id == 1929:
        #    scsy = 2
        #    inform_user(context, 'Set scoring system to 2')

        if scsy == 2:
            if a.leg.number == 1:
                # no prior work => regular grading system
                scsy = 0
            else:
                # concatenate review instructions for prior steps
                prior_steps = EstafetteLeg.objects.filter(
                    template=a.leg.template,
                    number__lt=a.leg.number)
                stph = lang.phrase('Step')
                for ps in prior_steps:
                    prior_rev_inst += ''.join(['<h3>', ps.title(stph), '</h3>',
                        ps.complete_review_instruction().split(STAR_DIVIDER)[0]]) 

        # temporary solution for storing two grades in the `grade` field
        grade_pair = divmod(ob_or_ap.grade, 256)
        # so grade_pair[1] = original grade, [0] grade for prior work

        context['referee_case'] = {
            'object': ob_or_ap,
            # NOTE: in the template, testing for ob will reveal that the case is an objection
            'ob': ob,
            'ap': ap,
            'lang': lang,
            'color': 'black' if ob else 'grey',
            'header_text': lang.phrase('Decide_on_this_' + ('objection' if ob else 'appeal')),
            # show names only to instructors
            'show_names': in_instructor_role,
            # add course relay properties
            'estafette_title': e.title(),
            'estafette_period': '{}&nbsp; {} &nbsp;{}&nbsp; {}.'.format(
                lang.phrase('Estafette_runs_from'),
                lang.ftime(e.start_time),
                lang.phrase('through'),
                lang.ftime(e.end_time)
                ),
            'estafette_desc': e.estafette.description,
            'scoring_system': scsy, 
            # add assignment properties
            'case_title': a.case.title(lang.phrase('Case')),
            'case_desc': ui_img(a.case.description),
            'step_title': a.leg.title(lang.phrase('Step')),
            'step_desc': a.leg.description,
            'prior_rev_inst': prior_rev_inst,
            'author': a.participant.student.dummy_name(),
            'time_uploaded': lang.ftime(a.time_uploaded),
            'pred_file_list': a.leg.file_list,
            'pred_hex': encode(a.id, context['user_session'].encoder),
            # add properties of the review that was appealed against
            'review': ar,
            'rev_items': ar.item_list(),
            'reviewer': ar.reviewer.student.dummy_name(),
            'time_reviewed': lang.ftime(ar.time_submitted),
            'time_appealed': lang.ftime(ar.time_appraised),
            # add properties concerning the appeal (but attributes of the PeerReview object)
            'imp_opinion': ''.join([
                lang.phrase('Pred_opinion_succ_work'),
                ' &nbsp;<tt>',
                lang.phrase(IMPROVEMENTS[ar.improvement_appraisal]),
                '</tt>'
                ]),
            'time_assigned': lang.ftime(ar.time_appeal_assigned),
            'deadline': lang.ftime(
                ar.time_appeal_assigned + timedelta(hours=48)
                ),
            'ribbon_color': (
                'red' if timezone.now() > ar.time_appeal_assigned + timedelta(
                    hours=30
                    )
                else 'orange'
                ),
            # add appeal properties
            'grade': grade_pair[1],
            'prior_grade': grade_pair[0],
            'graded': grade_pair[1] > 0 and (grade_pair[0] > 0 or scsy < 2),
            'words': word_count(ob_or_ap.grade_motivation),
            'min_words': e.minimum_appeal_word_count,
            'penalties_as_text': lang.penalties_as_text(
                ap.predecessor_penalty,
                ap.successor_penalty),
        }
        # only add time first viewed if such a view occurred
        if ap.time_first_viewed:
            context['referee_case']['time_viewed'] = lang.ftime(ap.time_first_viewed),
        # for objection cases, add objection properties
        if ob:
            # again: two grades in the `grade` field
            grade_pair = divmod(ap.grade, 256)
            # so grade_pair[1] = original grade, [0] grade for prior work
            context['referee_case'].update({
                'ap_grade': grade_pair[1],
                'ap_prior_grade': grade_pair[0],
                'referee': prefixed_user_name(ap.referee.user),
                # NOTE: referee ID hex is passed as double-check for objections 
                'referee_hex': encode(ob.referee.id, context['user_session'].encoder),
                'time_decided': lang.ftime(ap.time_decided),
                'objection_time_viewed': lang.ftime(ob.time_first_viewed),
                'new_penalties_as_text': lang.penalties_as_text(ob.predecessor_penalty, ob.successor_penalty)
            })
            # pass predecessor's appreciation of the appeal decision (if submitted)
            if ap.time_acknowledged_by_predecessor != DEFAULT_DATE:
                context['referee_case'].update({
                    'time_pred_appr': lang.ftime(ap.time_acknowledged_by_predecessor),
                    'pred_appr_icon': FACES[ap.predecessor_appraisal],
                    'pred_appr_color': COLORS[ap.predecessor_appraisal],
                    'pred_motiv': ap.predecessor_motivation,
                    'pred_objected': ap.is_contested_by_predecessor
                })
            # pass predecessor's appreciation of the appeal decision (if submitted)
            if ap.time_acknowledged_by_successor != DEFAULT_DATE:
                context['referee_case'].update({
                    'time_succ_appr': lang.ftime(ap.time_acknowledged_by_successor),
                    'succ_appr_icon': FACES[ap.successor_appraisal],
                    'succ_appr_color': COLORS[ap.successor_appraisal],
                    'succ_motiv': ap.successor_motivation,
                    'succ_objected': ap.is_contested_by_successor
                })
        # pass hex either for objection or for appeal
        context['referee_case']['hex'] = encode(ob.id if ob else ap.id, context['user_session'].encoder)
        # pass hex for case if it has a file attached
        if a.case.upload:
            context['referee_case']['case_hex'] = encode(a.case.id, context['user_session'].encoder)

    # NOTE: only show lists of refereeable objections and appeals if no case currently assigned to user
    if not (ob or ap):
        # NOTE: only instructors can decide on objections
        if in_instructor_role:
            # get the IDs of courses the instructor is teaching
            cids = Course.objects.filter(
                Q(instructors=context['user']) | Q(manager=context['user'])
                ).distinct().values_list('id')
            # get the objected appeals in ANY course estafette that are still unassigned as objection
            ap_list = Appeal.objects.filter(time_objection_assigned=DEFAULT_DATE
                # but only for relays in a course s/he is teaching 
                ).filter(review__reviewer__estafette__course__id__in=cids
                ).exclude(is_contested_by_predecessor=False, is_contested_by_successor=False
                ).exclude(review__reviewer__estafette__is_deleted=True
                # sort appeals in ascending order of date/time the appeal was made
                ).order_by('review__reviewer__estafette', 'review__assignment__leg__number',
                'review__assignment__case__letter', 'review__time_appraised')
            # create a list of objections for each course estafette
            context['ce_objections'] = []
            ce_nr = 0
            total_obs = 0
            if ap_list:
                prev_ce = None
                for ap in ap_list:
                    pr = ap.review
                    ce = pr.reviewer.estafette
                    if ce != prev_ce:
                        # add course language if it is not already in the list
                        # NOTE: this may occur when appeal is made in a course relay
                        #       for a course in which the user is not enrolled as student
                        lang = ce.course.language
                        if not lang.code in l_codes:
                            l_codes.append(lang.code)
                            context['languages'].append(lang)
                        ce_nr += 1
                        context['ce_objections'].append({
                            'nr': ce_nr,
                            'lang': lang,
                            'estafette_title': ce.title(),
                            'next_deadline': ce.next_deadline(),
                            'steps': ce.estafette.template.nr_of_legs(),
                            'objections': []
                            })
                        prev_ce = ce
                        a_nr = 0
                    a_nr += 1
                    a = pr.assignment
                    # add the review against which has been appealed
                    context['ce_objections'][ce_nr - 1]['objections'].append({
                        'nr': a_nr,
                        'appeal': ap,
                        'review': pr,
                        'time': lang.ftime(pr.time_appraised),
                        'hex': encode(ap.id, context['user_session'].encoder),
                        'code': a.case.letter + str(a.leg.number),
                        'case_title': a.case.title(lang.phrase('Case')),
                        'case': ui_img(a.case.description),
                        'step_title': a.leg.title(lang.phrase('Step')),
                        'step': ui_img(a.leg.description),
                        # show names only to instructors
                        'show_names': in_instructor_role,
                        'author_name': a.participant.student.dummy_name(),
                        'referee_name': prefixed_user_name(ap.referee.user)
                    })
                    total_obs += 1
            context['total_obs'] = total_obs

        # get the reviews -- ONLY for the legs for which the user is qualified --
        # in ANY course estafette that have been appealed and still unassigned as appeal case

        # get the IDs of the legs for which the user is qualified (used twice further below)
        # NOTE: for "focused" dummy users, this set is stored in the user session!
        if is_focused_user(context):
            uss = loads(context['user_session'].state)
            if 'referee_legs' in uss:
                lids = [l.id for l in uss['referee_legs']]
            else:
                lids = []
        else:
            qr_list = Referee.objects.filter(user=context['user'])
            lids = [qr.estafette_leg.id for qr in qr_list]

        pr_list = PeerReview.objects.filter(is_appeal=True, time_appeal_assigned=DEFAULT_DATE
            ).exclude(reviewer__estafette__is_deleted=True
            ).filter(assignment__leg__in=lids)
        # a user cannot arbitrate an appeal where s/he is the reviewer or appellant
        # UNLESS s/he is instructor in the course that comprises the estafette
        if in_instructor_role:
            pr_list = pr_list.filter(reviewer__student__course__in=cids)
        else:
            # NOTE: also exclude appeals made by team members (in any relay at any time)
            ul = list(sometime_team_partners(context['user']))
            # add the user him/herself to the list
            ul.append(context['user'])
            pr_list = pr_list.exclude(assignment__participant__student__user__in=ul
                ).exclude(reviewer__student__user__in=ul)

        # do not show appeals that are long overdue
        overduedate = timezone.now() - timedelta(days=MAX_DAYS_BEYOND_END_DATE)
        pr_list = pr_list.exclude(reviewer__estafette__review_deadline__lte=overduedate)

        # sort list in ascending order of date/time of the time the predecessor appealed
        pr_list = pr_list.order_by('reviewer__estafette', 'assignment__leg__number',
            'assignment__case__letter', 'time_appraised')
        # create a list of appeals for each course estafette
        context['ce_appeals'] = []
        ce_nr = 0
        total_appeals = 0
        if pr_list:
            prev_ce = None
            for pr in pr_list:
                ce = pr.reviewer.estafette
                if ce != prev_ce:
                    # add course language if it is not already in the list
                    # NOTE: this may occur when appeal is made in a course relay
                    #       for a course in which the user is not enrolled as student
                    lang = ce.course.language
                    if not lang.code in l_codes:
                        l_codes.append(lang.code)
                        context['languages'].append(lang)
                    ce_nr += 1
                    context['ce_appeals'].append({
                        'nr': ce_nr,
                        'lang': lang,
                        'estafette_title': ce.title(),
                        'next_deadline': ce.next_deadline(),
                        'steps': ce.estafette.template.nr_of_legs(),
                        'appeals': []
                        })
                    prev_ce = ce
                    a_nr = 0
                a_nr += 1
                a = pr.assignment
                # if NEITHER participant finished this estafette (almost), then this appeal is not urgent
                pred_subs = Assignment.objects.filter(participant=a.participant,
                    time_uploaded__gt=DEFAULT_DATE, clone_of__isnull=True).count()
                succ_subs = Assignment.objects.filter(participant=pr.reviewer,
                    time_uploaded__gt=DEFAULT_DATE, clone_of__isnull=True).count()
                min_subs = context['ce_appeals'][ce_nr - 1]['steps'] - 1
                # add the review against which has been appealed
                context['ce_appeals'][ce_nr - 1]['appeals'].append({
                    'nr': a_nr,
                    'review': pr,
                    'time': lang.ftime(pr.time_appraised),
                    'color': ('red'
                        if (timezone.now() - pr.time_appraised).days > 0
                        else 'black'
                        ), 
                    'hex': encode(pr.id, context['user_session'].encoder),
                    'code': a.case.letter + str(a.leg.number),
                    'case_title': ' '.join([
                        lang.phrase('Case'),
                        a.case.letter,
                        a.case.name
                        ]),
                    'case': ui_img(a.case.description),
                    'step_title': a.leg.title(lang.phrase('Step')),
                    'step': a.leg.description,
                    # show names only to instructors
                    'show_names': in_instructor_role,
                    'author_name': a.participant.student.dummy_name(),
                    'pred_subs': pred_subs,
                    'succ_subs': succ_subs,
                    'low_prio': (pred_subs < min_subs and succ_subs < min_subs)
                })
                total_appeals += 1
        context['total_appeals'] = total_appeals

    # AFTER THE REVIEW DEADLINE, course instructors will need to act as referee for assignments
    # submitted by participants who (almost) finished the estafette, but did not receive
    # a peer review for this assignment. Note that this may be because the successor did
    # not submit the review. Hence a query for SUBMITTED reviews.
    
    # NOTE: the following code only produces the list of instructor reviews that need to be
    #       done; the review forms are presented via the main loop over all participations
    #       (above); in this loop, the distinction between regular reviews, final reviews
    #       and instructor reviews is made.
    
    # first get all the user's "instructor students" (dummy_index < 0)
    # NOTE: do not do this when the user is a "focused" dummy, as then s/he has no instructor role
    total_post_reviews = 0
    if is_focused_user(context):
        csl = []
    else:
        # NOTE: exclude courses that are no longer active
        csl = CourseStudent.objects.filter(user=context['user'], dummy_index__lt=0
            ).exclude(course__end_date__lt=timezone.now())
    # get the IDs of all "past-deadline" course estafettes in which the user is "instructor-participant" 
    overduedate = timezone.now() - timedelta(days=MAX_DAYS_BEYOND_END_DATE)
    peids = Participant.objects.filter(student__in=[cs.id for cs in csl]
        ).filter(student__course__in=[cs.course.id for cs in csl]
        ).exclude(estafette__is_deleted=True
        ).exclude(estafette__start_time__gte=timezone.now()  # not started yet
        ).exclude(estafette__review_deadline__gte=timezone.now()  # still time to review
        ).exclude(estafette__review_deadline__lte=overduedate  # way over due date
        ).order_by('estafette__review_deadline').values_list('estafette__id', flat=True)
    context['instructor_estafettes'] = []
    ce_nr = 0
    # make a separate list for each of these estafettes
    for peid in peids:
        ce_nr += 1
        # get the number of legs for this estafette
        ce = CourseEstafette.objects.get(id=peid)
        leg_cnt = ce.estafette.template.nr_of_legs()
        # get the IDs of particpants who uploaded the all assignments
        pids = Assignment.objects.filter(participant__estafette__id=peid,
            ).filter(time_uploaded__gt=DEFAULT_DATE, leg__number=leg_cnt
            ).filter(participant__student__dummy_index=0
            ).values_list('participant_id', flat=True)
        # get all UPLOADED assignments of these finished participants
        ua_list = Assignment.objects.filter(participant__id__in=pids
            ).filter(time_uploaded__gt=DEFAULT_DATE, clone_of__isnull=True
            ).order_by('leg__number', 'case__letter', 'time_uploaded')
        # get the IDs of these assignments (for use in the following two filtering operations)
        uaids = [ua.id for ua in ua_list]
        # get all SUBMITTED reviews for these assignments
        prids = PeerReview.objects.filter(assignment__in=uaids,
            time_submitted__gt=DEFAULT_DATE).values_list('assignment__id', flat=True)
        # as well as reviews (also unsubmitted ones!) by "instructor participants"
        ipprids = PeerReview.objects.filter(assignment__in=uaids,
            reviewer__student__dummy_index__lt=0).values_list('assignment__id', flat=True)
        # both sets can be removed from the list of unreviewed assignments
        ua_list = ua_list.exclude(id__in=prids).exclude(id__in=ipprids)
        # if assignments remain, add their list (with other relevant info) to the context
        if ua_list:
            lang = ce.course.language
            # add this list  to the context 
            post_reviews = []
            ua_nr = 0
            for ua in ua_list:
                ua_nr += 1
                # add the assignment still needing a review
                post_reviews.append({
                    'nr': ua_nr,
                    'assignment': ua,
                    'time': lang.ftime(ua.time_uploaded),
                    'hex': encode(ua.id, context['user_session'].encoder),
                    'code': ua.case.letter + str(ua.leg.number),
                    'case_name': ua.case.name,
                    'step_name': ua.leg.name,
                    'author_name': ua.participant.student.dummy_name()
                })
            total_post_reviews += ua_nr
            # add course language if it is not already in the list
            if not lang.code in l_codes:
                l_codes.append(lang.code)
                context['languages'].append(lang)
            context['instructor_estafettes'].append({
                'nr': ce_nr,
                'lang': lang,
                'estafette_title': ce.title(),
                'next_deadline': ce.next_deadline(),
                'post_reviews': post_reviews
                })
    context['total_post_reviews'] = total_post_reviews
    context['page_title'] = 'Presto' 
    return render(request, 'presto/student.html', context)

