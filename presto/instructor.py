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
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone

from .models import (
    Course, CourseEstafette,
    Estafette, EstafetteCase, EstafetteTemplate,
    Participant, Profile
)

# python modules
from datetime import datetime, timedelta

# presto modules
from presto.generic import change_role, generic_context
from presto.utils import (decode, encode, prefixed_user_name,
    DATE_FORMAT, DATE_TIME_FORMAT, EDIT_STRING)

# view for instructor page
@login_required(login_url=settings.LOGIN_URL)
def instructor(request, **kwargs):
    context = generic_context(request)
    # check whether user can have instructor role
    if not change_role(context, 'Instructor'):
        return render(request, 'presto/forbidden.html', context)

    # create list of courses in which the user is manager/instructor
    context['courses'] = []
    c_set = Course.objects.filter(
        Q(instructors=context['user']) | Q(manager=context['user'])).distinct()
    for c in c_set:
        context['courses'].append({
            'object': c,
            'start': c.start_date.strftime(DATE_FORMAT),
            'end': c.end_date.strftime(DATE_FORMAT),
            'manager': prefixed_user_name(c.manager),
            'estafette_count': CourseEstafette.objects.filter(course=c).count(),
            'hex': encode(c.id, context['user_session'].encoder)
        })

    # create list of estafettes of which the user is creator/editor
    context['estafettes'] = [{
        'object': e,
        'edits': EDIT_STRING % (prefixed_user_name(e.last_editor),
            timezone.localtime(e.time_last_edit).strftime(DATE_TIME_FORMAT)),
        'template': e.template.name,
        'case_count': EstafetteCase.objects.filter(estafette=e).count(),
        'hex': encode(e.id, context['user_session'].encoder)
        } for e in Estafette.objects.filter(
            Q(editors=context['user']) | Q(creator=context['user'])).distinct()
    ]

    # create list of active project relays in which the user is instructor
    context['running_relays'] = [{
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
        } for ce in CourseEstafette.objects.filter(course__in=c_set, is_deleted=False
            ).exclude(start_time__gte=timezone.now()
            ).exclude(end_time__lte=timezone.now())
    ]
    
    # create list of estafette templates that the user can choose from
    context['templates'] = [{
        'object': et,
        'hex': encode(et.id, context['user_session'].encoder)
        } for et in EstafetteTemplate.objects.filter(published=True)
    ]
    
    context['page_title'] = 'Presto Instructor' 
    return render(request, 'presto/instructor.html', context)
