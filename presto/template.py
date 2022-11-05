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
from django.db import IntegrityError
from django.db.models import F
from django.shortcuts import render
from django.utils import timezone

# Python modules
from random import randrange

# Presto modules
from presto.generic import change_role, generic_context, report_error, warn_user
from presto.utils import (
    DATE_TIME_FORMAT,
    decode,
    EDIT_STRING,
    encode,
    log_message,
    plural_s,
    prefixed_user_name,
    ui_img
    )

from .models import (
    Estafette, EstafetteLeg, EstafetteTemplate,
    Language,
    Profile,
    random_hex32, Role
)

# view for template page
@login_required(login_url=settings.LOGIN_URL)
def template(request, **kwargs):
    h = kwargs.get('hex', '')
    context = generic_context(request, h)
    # check whether user can have developer role
    if not change_role(context, 'Developer'):
        return render(request, 'presto/forbidden.html', context)

    try:
        # check whether a new template is to be created
        if kwargs.get('action', '') == 'new':
            et = EstafetteTemplate(name=random_hex32())
            et.init_from_JSON('{"name": "New template", "description": "(template description)", '
                '"default_rules": "", "legs": []}', context['user'])

        # check whether estafette leg must be deleted
        elif kwargs.get('action', '') == 'delete-step':
            elid = decode(h, context['user_session'].decoder)
            el = EstafetteLeg.objects.get(pk=elid)
            et = el.template  # remember the template that is being edited
            n = el.number
            log_message(
                'Deleting step {} ({}) from template {}'.format(n, el.name, et.name),
                context['user']
                )
            el.delete()
            # now renumber all subsequent steps of this template
            EstafetteLeg.objects.filter(
                template=et,
                number__gt=n
                ).update(number=F('number') - 1)

        # check whether some leg is to be renumbered
        elif kwargs.get('action', '') in ['move-up', 'move-down']:
            elid = decode(h, context['user_session'].decoder)
            el = EstafetteLeg.objects.get(pk=elid)
            et = el.template  # remember the template that is being edited
            n = el.number
            if kwargs.get('action', '') == 'move-up':
                nn = n - 1
            else:
                nn = n + 1
            swap = EstafetteLeg.objects.filter(template=et).filter(number=nn)
            if len(swap) > 0:
                swel = swap.first()
                swel.number = randrange(9999, 999999999)  # to respect UNIQUE constraint
                swel.save()
                el.number = nn
                el.save()
                swel.number = n  # to respect UNIQUE constraint
                swel.save()
                log_message(
                    'Renumbered step {} from {} to {}'.format(el.name, n, nn),
                    context['user']
                    )
        # check whether the template is previewed
        elif kwargs.get('action', '') == 'preview':
            etid = decode(h, context['user_session'].decoder)
            et = EstafetteTemplate.objects.get(pk=etid)
            context['hex'] = encode(et.id, context['user_session'].encoder)
            context['object'] = et
            lang = Language.objects.filter(code='en-US').first()
            context['lang'] = lang
            context['edits'] = EDIT_STRING.format(
                name=prefixed_user_name(et.last_editor),
                time=timezone.localtime(et.time_last_edit).strftime(DATE_TIME_FORMAT)
                )
            # pass the leg data for the progress bar
            context['legs'] = [
                el for el in EstafetteLeg.objects.filter(
                    template=et
                    ).order_by('number')
                ]
            # see which task is previewed (default: "start, commit to rules")
            step = int(kwargs.get('step', 0))
            task = kwargs.get('task', 'c')
            if step == 0:
                if len(et.default_rules) > 0:
                    rules = et.default_rules
                else:
                    rules = lang.phrase('Rules_of_the_game')
                task_dict = {'type':'START', 'rules':rules}
            elif step > len(context['legs']):
                task_dict = {'type':'FINISH'}
                task = ''
            else:
                if step > 1 and task != 'p' and task != 's':
                    el = context['legs'][step - 2]
                else:
                    el = context['legs'][step - 1]
                task_dict = {'desc':el.description, 'file_list':el.file_list()}
            if task == 'p':
                n = len(context['legs']) - step + 1
                if n == 1:
                    steps_to_go = lang.phrase('One_more_step')
                else:
                    steps_to_go = lang.phrase('Steps_ahead').format(nr=n)
                task_dict.update({
                    'type':'PROCEED',
                    'task':'Proceed',
                    'steps_to_go':steps_to_go,
                    'header': lang.phrase('Proceed_header').format(
                        nr=el.number,
                        name=el.name)
                    })
            elif task == 'd':
                task_dict.update({
                    'type':'DOWNLOAD',
                    'task':'Download',
                    'icon':'download',
                    'header': lang.phrase('Download_header').format(
                        nr=el.number,
                        name=el.name)
                    })
            elif task == 'r':
                task_dict.update({
                    'type': 'REVIEW',
                    'task': 'Submit review',
                    'icon': 'star outline',
                    'header': lang.phrase('Review_header').format(
                        nr=el.number,
                        name=el.name
                        ),
                    'instr': ui_img(el.review_instruction),
                    'rejectable': el.rejectable
                    })
            elif task == 's':
                task_dict.update({
                    'type': 'SUBMIT',
                    'task': 'Submit',
                    'icon': 'upload',
                    'header': lang.phrase('Upload_header').format(
                        nr=el.number,
                        name=el.name
                        ),
                    'instr': el.upload_instruction,
                    'rev_instr': el.complete_review_instruction()
                    })
            context['task'] = task_dict
            # NOTE: after SUBMIT comes PROCEED to the NEXT step
            if task == 's':
                context['step'] = step
                context['next_step'] = step + 1
            else:
                context['step'] = step - 1
                context['next_step'] = step
            context['page_title'] = 'Presto template preview' 
            return render(request, 'presto/preview.html', context)
        # no step action? then hex identifies the selected template
        else:
            etid = decode(h, context['user_session'].decoder)
            et = EstafetteTemplate.objects.get(pk=etid)
            # check whether a new step is to be added
            if kwargs.get('action', '') == 'add-step':
                msg = ''
                n = EstafetteLeg.objects.filter(template=et).count() + 1
                el = EstafetteLeg.objects.create(
                        template = et,
                        name = 'New step ({})'.format(n),
                        number = n,
                        creator = context['user'],
                        time_created = timezone.now(),
                        last_editor = context['user'],
                        time_last_edit = timezone.now()
                    )
                log_message(
                    'Added {} to template {}'.format(el.name, et.name),
                    context['user']
                    )
    # catch-all for unanticipated errors
    except Exception as e:
        report_error(context, e) 
        return render(request, 'presto/error.html', context)

    # pass the template object and hex code
    # NOTE: formatted properties (dates) are rendered via AJAX calls
    context['template'] = {
        'object': et,
        'hex': encode(et.id, context['user_session'].encoder),
        'owner': prefixed_user_name(et.creator),
        'owned': et.creator == context['user'],
        # pass the names and hex IDs of editors
        'editors': [{
            'name': prefixed_user_name(e),
            'hex': encode(e.id, context['user_session'].encoder)
            } for e in et.editors.all()
        ],
        # also pass the list of legs in this template
        'legs': [{
            'object': el,
            'hex': encode(el.id, context['user_session'].encoder)
            } for el in EstafetteLeg.objects.filter(template=et)
        ]
    }

    # add hex IDs of all users having developer role (except course manager)
    ed_role = Role.objects.get(name='Developer')
    context['staff'] = [{
        'name': prefixed_user_name(p.user),
        'hex': encode(p.user.id, context['user_session'].encoder)
        } for p in Profile.objects.filter(roles__in=[ed_role]).exclude(user=context['user'])]

    context['page_title'] = 'Presto Developer' 
    return render(request, 'presto/template.html', context)

