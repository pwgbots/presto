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

from .models import EstafetteLeg, EstafetteTemplate, QuestionnaireTemplate

# presto modules
from presto.generic import change_role, generic_context, report_error
from presto.utils import (decode, encode, log_message, prefixed_user_name,
    DATE_FORMAT, DATE_TIME_FORMAT, EDIT_STRING)

# view for developer page
@login_required(login_url=settings.LOGIN_URL)
def developer(request, **kwargs):
    context = generic_context(request)
    # check whether user can have developer role
    if not change_role(context, 'Developer'):
        return render(request, 'presto/forbidden.html', context)

    # check whether a template must be deleted
    if kwargs.get('action', '') == 'delete-template':
        try:
            h = kwargs.get('hex', '')
            context = generic_context(request, h)
            etid = decode(h, context['user_session'].decoder)
            et = EstafetteTemplate.objects.get(pk=etid)
            log_message('Deleting template ' + et.name, context['user'])
            et.delete()
        except Exception as e:
            report_error(request, context, e)
            return render(request, 'presto/error.html', context)

    # pass list of estafette templates that the user is (co-)authoring
    context['templates'] = [{
        'object': t,
        'hex': encode(t.id, context['user_session'].encoder),
        'edits': EDIT_STRING.format(
            name=prefixed_user_name(t.last_editor),
            time=timezone.localtime(t.time_last_edit).strftime(DATE_TIME_FORMAT)
            ),
        'leg_count': EstafetteLeg.objects.filter(template=t).count()
        } for t in EstafetteTemplate.objects.filter(
            Q(editors=context['user']) | Q(creator=context['user'])).distinct()
    ]

    # TO DO: also pass list of questionnaire templates that the user is (co-)authoring
    context['questionnaires'] = [{
        'object': q,
        'hex': encode(q.id, context['user_session'].encoder),
        'edits': EDIT_STRING.format(
            name=prefixed_user_name(q.last_editor),
            time=timezone.localtime(q.time_last_edit).strftime(DATE_TIME_FORMAT)
            ),
        'item_count': 0, # to be changed!!
        } for q in QuestionnaireTemplate.objects.filter(
            Q(editors=context['user']) | Q(creator=context['user'])
            ).distinct()
    ]

    context['page_title'] = 'Presto Developer' 
    # show the developer page
    return render(request, 'presto/developer.html', context)

