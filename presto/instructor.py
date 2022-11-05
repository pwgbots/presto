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
from django.core.mail import EmailMessage
from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils.html import strip_tags

from .models import (
    Course,
    CourseEstafette,
    Estafette,
    EstafetteCase,
    EstafetteTemplate,
    Participant,
    Profile,
    )

# python modules
from datetime import date, datetime, timedelta
from io import open as io_open_file
import os
import sys
import traceback

# presto modules
from presto.generic import change_role, generic_context, inform_user, warn_user
from presto.utils import (
    DATE_FORMAT,
    DATE_TIME_FORMAT,
    decode,
    EDIT_STRING,
    encode,
    prefixed_user_name,
    plural_s,
    )


# HTML format for replies to questions
REPLY_HTML = """
{}
<div style="margin-top:12pt; margin-left:15pt">
<p>On {}, {} wrote:</p>
{}
</div>
"""


# view for instructor page
@method_decorator(csrf_exempt, name='dispatch')
@login_required(login_url=settings.LOGIN_URL)
def instructor(request, **kwargs):
    context = generic_context(request)
    # check whether user can have instructor role
    if not change_role(context, 'Instructor'):
        return render(request, 'presto/forbidden.html', context)

    # do whatever action is specified by the URL
    act = kwargs.get('action', '')
    # immediately check whether `hex` is passed as POST parameter
    qid = request.POST.get('hex', '')
    if act == 'reply' and qid:
        # validate the POST parameters
        # TO DO: implement with database object
        qpl = qid.split(';')
        sender = prefixed_user_name(User.objects.filter(username=qpl[0]).first())
        time_sent = datetime.strptime(qpl[1], '%Y%m%d%H%M').strftime(
            '%A, %d %B %Y, %H:%M'
            )
        case_letter = qpl[2]
        pids = [int(pid) for pid in qpl[3].split(',')]
        p_set = Participant.objects.filter(id__in=pids)
        path = os.path.join(settings.LOG_DIR, 'Q_{}_{}.html'.format(qpl[0], qpl[1]))
        html = ''
        r_html = request.POST.get('msg', '')
        # ensure that instructor's reply is not empty
        if not strip_tags(r_html).strip():
            warn_user(context, 'Your reply did not contain any text')
        # check if file exists
        elif not os.path.exists(path):
            warn_user(context, 'Question text file "{}" not found'.format(path))
        # check if at least one participant exists
        elif not p_set.first():
            warn_user(context, 'Participants #{} not recognized'.format(qpl[3]))
        else:
            # get the message content (HTML)
            try:
                with io_open_file(path, 'r', encoding='utf-8') as htmlfile:
                    html = htmlfile.read()
            except IOError:
                warn_user(context, 'Failed to read content from "{}"'.format(path))                    
        if html:
            ce = p_set.first().estafette
            # find question entry in file
            path = os.path.join(settings.LOG_DIR, 'RQL_{}.data'.format(ce.id))
            ok = True
            try:
                with io_open_file(path, 'rt', encoding='utf-8') as rqlfile:
                    lines = rqlfile.read()
                    if qid + '\n' in lines:
                        # if found, remove it
                        lines = lines.replace(qid + '\n', '')
                    else:
                        ok = False
                if ok:
                    with io_open_file(path, 'w', encoding='utf-8') as rqlfile:
                        rqlfile.write(lines)
            except IOError:
                ok = False
            if not ok:
                warn_user(
                    context,
                    'Failed to find/remove question entry in "{}"'.format(path)
                    )
            recip = ''
            try:
                # NOTE: send email even if a warning occurred
                email = EmailMessage(
                    strip_tags(ce.title()), # use relay title as subject
                    REPLY_HTML.format(r_html, time_sent, sender, html),
                    'no-reply@presto.tudelft.nl',  # discourage participants to reply by mail
                    [p.student.user.email for p in p_set],  # sent to all team members
                    [context['user'].email], # BCC to instructor
                )
                email.content_subtype = 'html'
                recip = ' to: ' + '; '.join(email.recipients())
                email.send()
                inform_user(context, 'E-mail sent', 'Your reply was mailed' + recip)
            except Exception as e:
                # also display the message contents, so it can be copied
                warn_user(context, 'Failed to send e-mail' + recip,
                    str(e) + '\n'.join([tb for tb in traceback.format_tb(sys.exc_info()[2])]))

    # create list of courses in which the user is manager/instructor
    context['courses'] = []
    context['closed_courses'] = []
    c_set = Course.objects.filter(
        Q(instructors=context['user']) | Q(manager=context['user'])).distinct()
    for c in c_set:
        # keep running and closed courses separate
        if c.end_date < date.today():
            k = 'closed_courses'
        else:
            k = 'courses'
        context[k].append({
            'object': c,
            'start': c.start_date.strftime(DATE_FORMAT),
            'end': c.end_date.strftime(DATE_FORMAT),
            'manager': prefixed_user_name(c.manager),
            'estafette_count': CourseEstafette.objects.filter(course=c).count(),
            'hex': encode(c.id, context['user_session'].encoder)
        })
    # also pass closed course count (with plural s)
    if context['closed_courses']:
        context['closed_course_count'] = plural_s(len(context['closed_courses']), 'course')

    # create list of estafettes of which the user is creator/editor
    context['estafettes'] = [{
        'object': e,
        'edits': EDIT_STRING.format(
            name=prefixed_user_name(e.last_editor),
            time=timezone.localtime(e.time_last_edit).strftime(DATE_TIME_FORMAT)
            ),
        'template': e.template.name,
        'case_count': EstafetteCase.objects.filter(estafette=e).count(),
        'hex': encode(e.id, context['user_session'].encoder)
        } for e in Estafette.objects.filter(
            Q(editors=context['user']) | Q(creator=context['user'])).distinct()
    ]

    # create list of active project relays in which the user is instructor
    ce_list = []
    ce_set = CourseEstafette.objects.filter(course__in=c_set, is_deleted=False, start_time__lt=timezone.now())
    for ce in ce_set:
        # NOTE: relays remain active until 90 days after their end time IF there still are pending decisions
        if ce.end_time >= timezone.now() or ce.pending_decisions():
            ce_list.append({
                'object': ce,
                'start_time': c.language.ftime(ce.start_time),
                'end_time': c.language.ftime(ce.end_time),
                'next_deadline': ce.next_deadline(),
                'participant_count': Participant.objects.filter(
                    estafette=ce, student__dummy_index__gt=-1).count(),
                'active_count': Participant.objects.filter(estafette=ce, student__dummy_index__gt=-1
                    ).filter(time_last_action__gte=timezone.now() - timedelta(days=1)).count(),
                'demo_code': ce.demonstration_code(),
                'hex': encode(ce.id, context['user_session'].encoder)
                })
    context['running_relays'] = ce_list


    # NOTE: temporary solution for participant questions
    q_list = []
    for r in context['running_relays']:
        # append question properties as one semicolon-separated line to the relay's question list
        path = os.path.join(settings.LOG_DIR, 'RQL_{}.data'.format(r['object'].id))
        if os.path.exists(path):
            with io_open_file(path, 'rt', encoding='utf-8') as rqlfile:
                lines = rqlfile.readlines()
                n = 0
                for l in lines:
                    n += 1
                    taken = False
                    u = None
                    qpl = l.strip().split(';')
                    if len(qpl) > 4:
                        u = User.objects.filter(username=qpl[4]).first()
                        taken = prefixed_user_name(u)
                    sender = User.objects.filter(username=qpl[0]).first()
                    dt = datetime.strptime(qpl[1], '%Y%m%d%H%M')
                    dts = dt.strftime('%d-%b-%Y %H:%M')
                    pids = [int(pid) for pid in qpl[3].split(',')]
                    p_set = Participant.objects.filter(id__in=pids)
                    q_dict = {
                        # NOTE: hex should become hex ID of Question object!
                        #       for now, pass on complete data line
                        'hex': l.strip(),
                        'case': qpl[2],
                        'time': dts,
                        'team': ', '.join([p.student.dummy_name() for p in p_set]),
                        'email': '; '.join([p.student.user.email for p in p_set]),
                        'taken': taken
                        }
                    q_list.append(q_dict)
                    # if user has taken on this question, add it in full to the context
                    if u and u.username == context['user'].username:
                        html = '<p>(failed to read content)</p>'
                        # TO DO: implement with database object!
                        path = os.path.join(
                            settings.LOG_DIR,
                            'Q_{}_{}.html'.format(qpl[0], qpl[1])
                            )
                        # check if file exists
                        if not os.path.exists(path):
                            log_message(
                                'Question text file "{}" not found'.format(path),
                                context['user']
                                )
                        else:
                            # get the message content (HTML)
                            try:
                                with io_open_file(path, 'r', encoding='utf-8') as htmlfile:
                                    html = htmlfile.read()
                            except IOError:
                                log_message(
                                    'Failed to read content from "{}"'.format(path),
                                    context['user']
                                    )
                        q_dict['time'] = dt.strftime(DATE_TIME_FORMAT)
                        q_dict['html'] = html
                        context['question'] = q_dict
                r['q_count'] = n
    context['questions'] = q_list
    
    # create list of estafette templates that the user can choose from
    context['templates'] = [{
        'object': et,
        'hex': encode(et.id, context['user_session'].encoder)
        } for et in EstafetteTemplate.objects.filter(published=True)
    ]
    
    context['page_title'] = 'Presto Instructor' 
    return render(request, 'presto/instructor.html', context)
