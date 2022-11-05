# Software developed by Pieter W.G. Bots for the PrESTO project
# Code repository: https://github.com/pwgbots/presto
# Project wiki: http://presto.tudelft.nl/wiki

"""
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
from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .models import (
    Course, CourseEstafette, CourseStudent,
    Estafette, EstafetteLeg, EstafetteTemplate,
    Language,
    Participant, Profile,
    Role,
    QuestionnaireTemplate
)

# python modules
from datetime import datetime, timedelta

# presto modules
from presto.badge import disc_and_color
from presto.generic import change_role, generic_context, report_error, warn_user
from presto.uiphrases import UI_LANGUAGE_CODES
from presto.utils import (decode, encode, log_message, prefixed_user_name,
    string_to_datetime, DATE_FORMAT)


# view for course page that processes POST data with own CSRF protection (using encode/decode)
@method_decorator(csrf_exempt, name='dispatch')
@login_required(login_url=settings.LOGIN_URL)
def course(request, **kwargs):
    h = kwargs.get('hex', '')
    act = kwargs.get('action', '')
    context = generic_context(request, h)
    # check whether user can view this course
    try:
        cid = decode(h, context['user_session'].decoder)
        if act == 'delete-relay':
            # in this case, the course relay ID is passed as hex
            ce = CourseEstafette.objects.get(pk=cid)
            c = ce.course
        else:
            # otherwise the course ID
            c = Course.objects.get(pk=cid)
        # ensure that user is instructor in the course
        if not (c.manager == context['user'] or c.instructors.filter(id=context['user'].id)):
            log_message('ACCESS DENIED: Invalid course parameter', context['user'])
            return render(request, 'presto/forbidden.html', context)
    except Exception as e:
        report_error(context, e)
        return render(request, 'presto/error.html', context)

    # if relay is to be deleted, try to do this
    if act == 'delete-relay':
        try:
            # check whether indeed the instructor is the only participant
            if Participant.objects.filter(estafette=ce, student__dummy_index__gt=-1).count() == 0:
                # if so, delete the instructor participant
                Participant.objects.filter(estafette=ce, student__dummy_index=-1).delete()
                # and then delete the course relay itself
                ce.delete()
            else:
                # otherwise, only set the "is deleted" property so that it will no longer show
                ce.is_deleted = True
                ce.save()
        except:
            warn_user(context, 'Failed to delete course relay',
                'Please report this error to the Presto administrator.')

    # otherwise process form input (if any)
    elif len(request.POST) > 0:
        try:
            eid = decode(request.POST.get('relay', ''), context['user_session'].decoder)
            qid = decode(request.POST.get('questionnaire', ''), context['user_session'].decoder)
            ce = CourseEstafette(course=c,
                estafette=Estafette.objects.get(pk=eid),
                suffix=request.POST.get('suffix', ''),
                start_time=datetime.strptime(request.POST.get('starts', ''), '%Y-%m-%d %H:%M'),
                deadline=datetime.strptime(request.POST.get('deadline', ''), '%Y-%m-%d %H:%M'),
                review_deadline=datetime.strptime(request.POST.get('revsdue', ''), '%Y-%m-%d %H:%M'),
                end_time=datetime.strptime(request.POST.get('ends', ''), '%Y-%m-%d %H:%M'),
                questionnaire_template=QuestionnaireTemplate.objects.get(pk=qid),
                final_reviews=int(request.POST.get('reviews', ''))
            )
            ce.save()
            log_message('Added new estafette to course', context['user'])
        except Exception as e:
            report_error(context, e)
            return render(request, 'presto/error.html', context)
    
    # add course properties that need conversion to context
    context['course'] = {
        'object': c,
        'start': c.language.fdate(c.start_date),
        'end': c.language.fdate(c.end_date),
        'manager': prefixed_user_name(c.manager),
        'owned': c.manager == context['user'],
        'instructors': [{
            'name': prefixed_user_name(i),
            'hex': encode(i.id, context['user_session'].encoder)
            } for i in c.instructors.all()
        ],
        'hex':  encode(c.id, context['user_session'].encoder),
        'disc': (c.badge_color >> 24) & 15,
        'red': (c.badge_color >> 16) & 255,
        'green': (c.badge_color >> 8) & 255,
        'blue': c.badge_color & 255
    }

    # add available language codes (for drop-down in form)
    context['lang_codes'] = UI_LANGUAGE_CODES
    
    # add hex IDs of all users having instructor role (except course manager)
    i_role = Role.objects.get(name='Instructor')
    context['staff'] = [{
        'name': prefixed_user_name(p.user),
        'hex': encode(p.user.id, context['user_session'].encoder)
        } for p in Profile.objects.filter(roles__in=[i_role]).exclude(user=context['user'])]

    # add available estafettes and questionnaire templates (for drop-downs in form)
    context['estafettes'] = [{
        'name': e.name,
        'desc': e.description,
        'hex': encode(e.id, context['user_session'].encoder)
        } for e in Estafette.objects.filter(published=True)
    ]
    context['questionnaires'] = [{
        'name': t.name,
        'desc': t.description,
        'hex': encode(t.id, context['user_session'].encoder)
        } for t in QuestionnaireTemplate.objects.filter(published=True)
    ]

    # add number of enrolled students
    context['course']['students'] = CourseStudent.objects.filter(course=c, dummy_index=0).count()

    # add list of run(ning) estafettes
    context['course']['estafettes'] = [{
        'object': ce,
        'start_time': c.language.ftime(ce.start_time),
        'end_time': c.language.ftime(ce.end_time),
        'next_deadline': ce.next_deadline(),
        'participant_count': Participant.objects.filter(
            estafette=ce, student__dummy_index__gt=-1).count(),
        'active_count': Participant.objects.filter(estafette=ce, student__dummy_index__gt=-1
            ).filter(time_last_action__gte=timezone.now() - timedelta(days=1)).count(),
        'demo_code': ce.demonstration_code(),
        'consumer_secret': ce.LTI_consumer_secret(),
        'hex': encode(ce.id, context['user_session'].encoder)
        } for ce in CourseEstafette.objects.filter(course=c, is_deleted=False)
    ]
    context['page_title'] = 'Presto Course' 
    return render(request, 'presto/course.html', context)


