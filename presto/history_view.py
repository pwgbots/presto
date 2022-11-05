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
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.db.models.aggregates import Min
from django.shortcuts import render
from django.utils import timezone

from .models import (
    Appeal,
    Assignment,
    Course,
    CourseEstafette,
    CourseStudent,
    DEFAULT_DATE,
    Estafette,
    EstafetteCase,
    EstafetteLeg,
    Objection,
    Participant,
    PeerReview
    )

# presto modules
from presto.generic import (
    change_role,
    generic_context,
    has_role,
    report_error
    )
from presto.teams import (
    team_as_html,
    team_assignments,
    team_final_reviews,
    team_given_reviews,
    team_submissions,
    team_user_downloads,
    things_to_do
    )
from presto.utils import (
    COLORS,
    DATE_FORMAT,
    DATE_TIME_FORMAT,
    decode,
    EDIT_STRING,
    encode,
    FACES,
    log_message,
    OPINIONS,
    prefixed_user_name,
    ui_img,
    YOUR_OPINIONS
    )


@login_required(login_url=settings.LOGIN_URL)
def history_view(request, **kwargs):
    """
    Return the view for a student's project relay history.
    """
    h = kwargs.get('hex', '')
    context = generic_context(request, h)
    # check whether user can have student role
    if not change_role(context, 'Student'):
        return render(request, 'presto/forbidden.html', context)
        
    # check whether user is enrolled in any courses
    cl = Course.objects.filter(coursestudent__user=context['user']
        ).annotate(count=Count('coursestudent'))
    # add this list in readable form to the context (showing multiple enrollments)
    context['course_list'] = ',&nbsp;&nbsp; '.join([
        c.title() + (
            ' <span style="font-weight: 800; color: red">{}&times;</span>'.format(
                c.count if c.count > 1 else ''
                )
            ) for c in cl
        ])

    # student (but also instructor in that role) may be enrolled in several courses
    # NOTE: "dummy" students are included, but not the "instructor" students
    csl = CourseStudent.objects.filter(user=context['user'], dummy_index__gt=-1)

    # get the estafettes for all the student's courses (even if they are not active)
    cel = CourseEstafette.objects.filter(
        is_deleted=False, is_hidden=False, course__in=[cs.course.id for cs in csl])
    # add this list in readable form to the context
    context['estafette_list'] = ',&nbsp;&nbsp; '.join([ce.title() for ce in cel])

    # get the set of all the course student's current participations
    pl = Participant.objects.filter(estafette__is_deleted=False,
        estafette__is_hidden=False, student__in=[cs.id for cs in csl]
        ).order_by('-estafette__start_time')
    
    # if user is a "focused" dummy user, retain only this course user's participations
    if 'alias' in context:
        pl = pl.filter(student=context['csid'])

    # if h is not set, show the list of participations as a menu
    if h == '':
        # start with an empty list (0 participations)
        context['participations'] = []
        # for each participation, create a context entry with properties to be displayed
        for p in pl:
            lang = p.estafette.course.language  # estafettes "speak" the language of their course
            steps = p.estafette.estafette.template.nr_of_legs()
            part = {'object': p,
                    'lang': lang,
                    'start': lang.ftime(p.estafette.start_time),
                    'end': lang.ftime(p.estafette.end_time),
                    'next_deadline': p.estafette.next_deadline(),
                    'steps': steps,
                    'hex': encode(p.id, context['user_session'].encoder),
                    'progress': team_submissions(p),
                    }
            context['participations'].append(part)
        # and show the list as a menu
        context['page_title'] = 'Presto History' 
        return render(request, 'presto/history_view.html', context)

    # if we get here, h is set, which means that a specific estafette has been selected
    try:
        # first validate the hex code
        pid = decode(h, context['user_session'].decoder)
        p = Participant.objects.get(pk=pid)
        context['object'] = p
        # encode again, because used to get progress chart
        context['hex'] = encode(p.id, context['user_session'].encoder)
        # add progress bar data
        context['things_to_do'] = things_to_do(p)
        # do not add participant name popups
        context['identify'] = False
        # add context fields to be displayed when rendering the template
        set_history_properties(context, p)
        # show the full estafette history using the standard page template
        context['page_title'] = 'Presto History' 
        return render(request, 'presto/estafette_history.html', context)        
            
    except Exception as e:
        report_error(context, e)
        return render(request, 'presto/error.html', context)


# NOTE: this function is also used by the ajax call 'participant history'
def set_history_properties(context, p):
    # switch to the course language
    lang = p.estafette.course.language
    # add the language-sensitive properties to the context
    context['lang'] = lang
    context['committed'] = p.time_started > DEFAULT_DATE
    context['last_action'] = lang.ftime(p.student.last_action)
    context['start'] = lang.ftime(p.estafette.start_time)
    context['end'] = lang.ftime(p.estafette.end_time)
    context['desc'] = p.estafette.estafette.description
    context['next_deadline'] = p.estafette.next_deadline()
    context['team'] = team_as_html(p)
    context['decisions'] = []
    
    # NOTE: first see whether participant has decided on appeals in this estafette
    ap_list = Appeal.objects.filter(referee__user=p.student.user
        ).filter(review__reviewer__estafette=p.estafette).exclude(time_decided=DEFAULT_DATE
        ).order_by('time_decided')
    if ap_list:
        # create a list of decided appeals for this course estafette
        ap_nr = 0
        for ap in ap_list:
            ap_nr += 1
            # add the appeal that has been decided
            ap_dict = decided_appeal_dict(context, ap, lang)
            ap_dict['nr'] = ap_nr
            context['decisions'].append(ap_dict)

    # now compile a consecutive list of all the student's actions in this estafette
    # (1) get list of all assignments for the student so far (except rejections and clones!)
    a_list = team_assignments(p).order_by('leg__number')
    # from this list, derive a list with only the primary keys of the assignments
    aid_list = [a.id for a in a_list]
    # (2) get list of all reviews the student has written so far
    pr_given = team_given_reviews(p).exclude(time_submitted=DEFAULT_DATE)
    # (3) also get list of all reviews the student has received so far
    pr_received = PeerReview.objects.filter(assignment__id__in=aid_list
        ).exclude(time_submitted=DEFAULT_DATE)
    # (4) also get the "oldest" user download objects for the assignment set
    ud_set = team_user_downloads(p, aid_list).annotate(first_download_at=Min('time_downloaded'))
    # process the assignments in their number sequence
    steps = []
    for a in a_list:
        # show all the student's assignments (i.e., also those without file uploads)
        step_nr = a.leg.number
        step = {
            'step_nr': step_nr,
            'assignment': a,
            'header': lang.phrase('Step_header').format(nr=step_nr, name=a.leg.name),
            # indicate whether the student did upload this step (or file list should not be shown)
            'uploaded': (a.time_uploaded != DEFAULT_DATE),
            'time': lang.ftime(a.time_uploaded),
            'case_title': a.case.title(lang.phrase('Case')),
            'case': ui_img(a.case.description),
            'desc': a.leg.description,
            'rev_instr': a.leg.complete_review_instruction(),
            'Assigned_to_you': (
                lang.phrase('Assigned_to_you') + lang.ftime(a.time_assigned)
                ),
            'You_uploaded': (
                lang.phrase('You_uploaded') + lang.ftime(a.time_uploaded)
                ),
            'upl_items': a.item_list(),
            'own_file_list': a.leg.file_list(),
            'pred_file_list': [],
            'succ_file_list': [],
            'pred_reviews': [],
            'succ_reviews': [],
            'own_hex': encode(a.id, context['user_session'].encoder)
        }
        # pass hex for case if it has a file attached
        if a.case.upload:
            step['case_hex'] = encode(a.case.id, context['user_session'].encoder)
        # add half point bonus statement if such bonus was earned
        if a.on_time_for_bonus():
            step['time_bonus'] = lang.phrase('Half_point_bonus')

        # for all but the first step, also show the review(s) the student has given on preceding steps
        if step_nr > 1:
            # the file list is step-specific, but not review-specific
            step['pred_file_list'] = a.predecessor.leg.file_list()
            step['pred_hex'] = encode(a.predecessor.id, context['user_session'].encoder)
            # get the first user download (if any)
            fud = ud_set.filter(assignment__id=a.id).first()
            if fud:
                step['downloaded'] = lang.ftime(fud.first_download_at)
            # the student may have given several reviews: rejections and second opinions
            prgl = pr_given.filter(assignment__leg__number=step_nr - 1).order_by('time_submitted')
            # add these reviews to this step
            for pr in prgl:
                step['pred_reviews'].append(given_review_dict(context, pr, lang))

        # the student may also have received reviews of own work
        prrl = pr_received.filter(assignment__leg__number=step_nr).order_by('time_submitted')
        for pr in prrl:
            # do not show reviews that have been saved, but for which the successor did NOT
            # upload yet (unless it is a rejection or a FINAL review or a second opinion,
            # OR the deadline for reviews is past)
            if not (pr.is_rejection or pr.is_second_opinion or pr.final_review_index):
                # to prevent all error, double-check whether there IS a successor
                # NOTE: if reviewer is "instructor student", then skip the upload check
                if pr.assignment.successor and not (pr.reviewer.student.dummy_index < 0):
                    if (pr.assignment.successor.time_uploaded == DEFAULT_DATE
                        and timezone.now() < p.estafette.review_deadline):
                        continue  # skip this review, but continue looping
            r = {
                'object': pr,
                'time_submitted': lang.ftime(pr.time_submitted),
                'rev_items': pr.item_list()
                # no 'pred_hex' field, as the reviewed work is the student's own step
            }
            # if student has responded, additional fields must be added
            if pr.time_appraised != DEFAULT_DATE:
                r['time_appraised'] = lang.ftime(pr.time_appraised)
                r['app_icon'] = FACES[pr.appraisal]
                r['app_header'] = lang.phrase('Your_appraisal_header').format(
                    opinion=lang.phrase(YOUR_OPINIONS[pr.appraisal])
                    )
            # student can see reviewer's work only if review is not a rejection,
            # a second opinion, or a final review (which has by definition no successor)
            if not (pr.is_rejection or pr.is_second_opinion or pr.final_review_index):
                # to prevent all error, double-check whether there IS a successor
                if pr.assignment.successor:
                    step['succ_file_list'] = pr.assignment.successor.leg.file_list()
                    step['succ_hex'] = encode(pr.assignment.successor.id, context['user_session'].encoder)
                r['imp_opinion'] = ''.join([
                    lang.phrase('Your_opinion_on_improvement'),
                    '<tt>',
                    lang.phrase(
                        ['Pass', 'No_improvement', 'Minor_changes',
                         'Good_job'][pr.improvement_appraisal]
                        ),
                    '</tt>'
                    ])
            # in case of an appeal, report the appeal status
            if pr.is_appeal:
                if pr.time_appeal_assigned != DEFAULT_DATE:
                    r['time_assigned'] = lang.ftime(pr.time_appeal_assigned)
                    ap = Appeal.objects.filter(review=pr).first()
                    if ap:
                        # NOTE: grade may encode two scores
                        prior_grade, grade = divmod(ap.grade, 256)
                        r['referee'] = prefixed_user_name(ap.referee.user)
                        if ap.time_first_viewed != DEFAULT_DATE:
                            r['time_first_viewed'] = lang.ftime(ap.time_first_viewed)
                        if ap.time_decided != DEFAULT_DATE:
                            r['time_decided'] = lang.ftime(ap.time_decided)
                            r['ref_prior_rat'] = prior_grade
                            r['ref_rat'] = grade
                            r['ref_motiv'] = ap.grade_motivation
                            r['penalties'] = lang.penalties_as_text(
                                ap.predecessor_penalty, ap.successor_penalty)
                        # NOTE: in this case, the student ("you") is the predecessor ...
                        if ap.time_acknowledged_by_predecessor != DEFAULT_DATE:
                            r['time_your_appr'] = lang.ftime(ap.time_acknowledged_by_predecessor)
                            r['your_appr_icon'] = FACES[ap.predecessor_appraisal]
                            r['your_motiv'] = ap.predecessor_motivation
                            r['you_objected'] = ap.is_contested_by_predecessor
                        # ... and hence the other party the successor
                        if ap.time_acknowledged_by_successor != DEFAULT_DATE:
                            r['time_other_appr'] = lang.ftime(ap.time_acknowledged_by_successor)
                            r['other_appr_icon'] = FACES[ap.successor_appraisal]
                            r['other_motiv'] = ap.successor_motivation
                            r['other_objected'] = ap.is_contested_by_successor
                        # see if this appeal may have an associated objection
                        if ap.is_contested_by_predecessor or ap.is_contested_by_successor:
                            ob = Objection.objects.filter(appeal=ap).exclude(time_decided=DEFAULT_DATE).first()
                            if ob:
                                # NOTE: again, grade may encode two scores
                                prior_grade, grade = divmod(ob.grade, 256)
                                r['ob'] = ob
                                r['ob_time_decided'] = lang.ftime(ob.time_decided)
                                r['ob_prior_rat'] = prior_grade
                                r['ob_rat'] = grade
                                r['ob_penalties_as_text'] = lang.penalties_as_text(ob.predecessor_penalty, ob.successor_penalty)
            # add the review to the list
            step['succ_reviews'].append(r)
        # now all step properties have been set, so the step is added to the list
        steps.append(step)            
    # and finally the step list is added to the context
    context['steps'] = steps

    # the student may also have given final reviews
    context['final_reviews'] = []
    prgl = pr_given.filter(final_review_index__gt=0).order_by('final_review_index')
    # add these reviews to this step
    n = 0
    for pr in prgl:
        r = given_review_dict(context, pr, lang)
        n += 1
        r['nr'] = n
        a = pr.assignment
        r['header'] = lang.phrase('Final_review_header').format(
            nr=step_nr,
            name=a.leg.name)
        r['case_title'] = a.case.title(lang.phrase('Case'))
        r['case'] = a.case.description.replace(
            '<img ',
            '<img class="ui large image" '
            )
        # pass hex for case if it has a file attached
        if a.case.upload:
            r['case_hex'] = encode(a.case.id, context['user_session'].encoder)
        r['rev_instr'] = a.leg.complete_review_instruction()
        r['pred_file_list'] = a.leg.file_list()
        context['final_reviews'].append(r)


# returns dictionary with properties of peer review pr that are used by the rendering template
def given_review_dict(context, pr, lang):
    tfd = team_user_downloads(pr.reviewer, [pr.assignment.id])
    if tfd:
        tfd = tfd.first().time_downloaded
    else:
        tfd = DEFAULT_DATE
    r = {
        'object': pr,
        'lang': lang,
        'time_first_download': lang.ftime(tfd),
        'time_submitted': lang.ftime(pr.time_submitted),
        'rev_items': pr.item_list(),
        'pred_hex': encode(pr.assignment.id, context['user_session'].encoder)
    }
    # if predecessor has responded, additional fields must be added
    if pr.time_appraised != DEFAULT_DATE:
        r['time_appraised'] = lang.ftime(pr.time_appraised)
        r['app_icon'] = FACES[pr.appraisal]
        r['app_header'] = lang.phrase('Appraisal_header').format(
            opinion=lang.phrase(OPINIONS[pr.appraisal])
            )
        r['imp_opinion'] = ''.join([
            lang.phrase('Opinion_on_sucessor_version'),
            ' &nbsp;<tt>',
            lang.phrase(
                ['Pass', 'No_improvement', 'Minor_changes',
                 'Good_job'][pr.improvement_appraisal]
                ),
            '</tt>'
            ])
    # also indicate whether student has acknowledged
    if pr.time_acknowledged != DEFAULT_DATE:
        r['time_acknowledged'] = lang.ftime(pr.time_acknowledged)
    # in case of an appeal, report the appeal status
    if pr.is_appeal:
        if pr.time_appeal_assigned != DEFAULT_DATE:
            r['time_assigned'] = lang.ftime(pr.time_appeal_assigned)
            ap = Appeal.objects.filter(review=pr).first()
            if ap:
                r['referee'] = prefixed_user_name(ap.referee.user)
                if ap.time_first_viewed != DEFAULT_DATE:
                    r['time_first_viewed'] = lang.ftime(ap.time_first_viewed)
                if ap.time_decided != DEFAULT_DATE:
                    r['time_decided'] = lang.ftime(ap.time_decided)
                    # NOTE: grade may encode two scores
                    prior_grade, grade = divmod(ap.grade, 256)
                    r['ref_rat'] = grade
                    r['ref_prior_rat'] = prior_grade
                    r['ref_motiv'] = ap.grade_motivation
                    r['penalties'] = lang.penalties_as_text(
                        ap.predecessor_penalty, ap.successor_penalty)
                # NOTE: in this case, the student ("you") is the successor ...
                if ap.time_acknowledged_by_successor != DEFAULT_DATE:
                    r['time_your_appr'] = lang.ftime(ap.time_acknowledged_by_successor)
                    r['your_appr_icon'] = FACES[ap.successor_appraisal]
                    r['your_motiv'] = ap.successor_motivation
                    r['you_objected'] = ap.is_contested_by_successor
                # ... and hence the other party the predecessor
                if ap.time_acknowledged_by_predecessor != DEFAULT_DATE:
                    r['time_other_appr'] = lang.ftime(ap.time_acknowledged_by_predecessor)
                    r['other_appr_icon'] = FACES[ap.predecessor_appraisal]
                    r['other_motiv'] = ap.predecessor_motivation
                    r['other_objected'] = ap.is_contested_by_predecessor
                # see if this appeal may have an associated objection
                if ap.is_contested_by_predecessor or ap.is_contested_by_successor:
                    ob = Objection.objects.filter(appeal=ap).exclude(time_decided=DEFAULT_DATE).first()
                    if ob:
                        r['ob'] = ob
                        r['ob_time_decided'] = lang.ftime(ob.time_decided)
                        r['ob_penalties_as_text'] = lang.penalties_as_text(ob.predecessor_penalty, ob.successor_penalty)
    return r


# returns dict with properties of an appeal such that they can be rendered
def decided_appeal_dict(context, ap, lang):
    ar = ap.review
    a = ar.assignment
    # NOTE: grade may encode two scores
    prior_grade, grade = divmod(ap.grade, 256)
    d = {
        'appeal': ap,
        'appeal_title': '{} {}{} <span style="margin-left: 1em; font-weight: 500">({})</span>'.format(
            lang.phrase('Appeal_case_decision'),
            a.case.letter,
            str(a.leg.number),
            lang.ftime(ap.time_decided)
            ),
        # show names only to instructors
        'show_names': has_role(context, 'Instructor'),
        # add assignment properties
        'case_title': a.case.title(lang.phrase('Case')),
        'case_desc': ui_img(a.case.description),
        'step_title': a.leg.title(lang.phrase('Step')),
        'step_desc': a.leg.description,
        'author': a.participant.student.dummy_name(),
        'time_uploaded': lang.ftime(a.time_uploaded),
        'pred_file_list': a.leg.file_list,
        'pred_hex': encode(a.id, context['user_session'].encoder),
        # add properties of the review that is appealed against
        'review': ar,
        'rev_items': ar.item_list(),
        'reviewer': ar.reviewer.student.dummy_name(),
        'time_reviewed': lang.ftime(ar.time_submitted),
        'time_appealed': lang.ftime(ar.time_appraised),
        # add properties concerning the appeal (but attributes of the PeerReview object)
        'imp_opinion': ''.join([
            lang.phrase('Pred_opinion_succ_work'),
            ' &nbsp;<tt>',
            lang.phrase(['Pass', 'No_improvement', 'Minor_changes',
                         'Good_job'][ar.improvement_appraisal]),
            '</tt>'
            ]),
        'time_assigned': lang.ftime(ar.time_appeal_assigned),
        # add appeal properties
        'time_decided': lang.ftime(ap.time_decided),
        'prior_grade': prior_grade,
        'grade': grade,
        'penalties_as_text': lang.penalties_as_text(ap.predecessor_penalty, ap.successor_penalty),
        'hex': encode(ap.id, context['user_session'].encoder)
    }
    # pass time first viewed only if such view occurred
    if ap.time_first_viewed != DEFAULT_DATE:
        d['time_viewed'] = lang.ftime(ap.time_first_viewed)
    # pass hex for case if it has a file attached
    if a.case.upload:
        d['case_hex'] = encode(a.case.id, context['user_session'].encoder)
    # pass predecessor's appreciation of the decision (if submitted)
    if ap.time_acknowledged_by_predecessor != DEFAULT_DATE:
        d['time_pred_appr'] = lang.ftime(ap.time_acknowledged_by_predecessor)
        d['pred_appr_icon'] = FACES[ap.predecessor_appraisal]
        d['pred_appr_color'] = COLORS[ap.predecessor_appraisal]
        d['pred_motiv'] = ap.predecessor_motivation
        d['pred_objected'] = ap.is_contested_by_predecessor
    # pass predecessor's appreciation of the decision (if submitted)
    if ap.time_acknowledged_by_successor != DEFAULT_DATE:
        d['time_succ_appr'] = lang.ftime(ap.time_acknowledged_by_successor)
        d['succ_appr_icon'] = FACES[ap.successor_appraisal]
        d['succ_appr_color'] = COLORS[ap.successor_appraisal]
        d['succ_motiv'] = ap.successor_motivation
        d['succ_objected'] = ap.is_contested_by_successor
    # see if this appeal may have an associated objection
    if ap.is_contested_by_predecessor or ap.is_contested_by_successor:
        ob = Objection.objects.filter(appeal=ap).exclude(time_decided=DEFAULT_DATE).first()
        if ob:
            # NOTE: grade may encode two scores
            prior_grade, grade = divmod(ob.grade, 256)
            d['ob'] = ob
            d['ob_time_decided'] = lang.ftime(ob.time_decided)
            d['ob_prior_grade'] = prior_grade
            d['ob_grade'] = grade
            d['ob_penalties_as_text'] = lang.penalties_as_text(ob.predecessor_penalty, ob.successor_penalty)
    return d

