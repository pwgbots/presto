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
from django.shortcuts import render
from django.utils import timezone

from .models import Estafette, EstafetteCase, Profile, Role, UserSession

# presto modules
from presto.generic import change_role, generic_context, report_error
from presto.utils import (
    DATE_TIME_FORMAT,
    decode,
    encode,
    EDIT_STRING,
    log_message,
    prefixed_user_name,
    ui_img
    )


# view for estafette page (for instructors authoring an estafette)
@login_required(login_url=settings.LOGIN_URL)
def estafette_view(request, **kwargs):
    h = kwargs.get('hex', '')
    context = generic_context(request, h)
    # check whether user can have instructor role
    if not change_role(context, 'Instructor'):
        return render(request, 'presto/forbidden.html', context)
    
    # check whether estafette case must be deleted
    if kwargs.get('action', '') == 'delete-case':
        try:
            ecid = decode(h, context['user_session'].decoder)
            ec = EstafetteCase.objects.get(pk=ecid)
            # remember the estafette that is being edited
            e = ec.estafette
            ec.delete()
        except Exception as e:
            report_error(context, e)
            return render(request, 'presto/error.html', context)
    else:
        # if no deletion, the selected estafette is passed as hex code
        try:
            eid = decode(h, context['user_session'].decoder)
            e = Estafette.objects.get(pk=eid)
        except Exception as e:
            report_error(context, e)
            return render(request, 'presto/error.html', context)
        # check whether a new case is to be added
        if kwargs.get('action', '') == 'add-case':
            ec_list = EstafetteCase.objects.filter(estafette=e)
            # find first unused letter in the alfabet
            for l in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                if not ec_list.filter(letter=l):
                    break
            ec = EstafetteCase.objects.create(
                    estafette = e,
                    name = 'New case ({})'.format(l),
                    letter = l,
                    creator = context['user'],
                    time_created = timezone.now(),
                    last_editor = context['user'],
                    time_last_edit = timezone.now()
                )

    # when no errors, create list of cases in this estafette
    ec_list = EstafetteCase.objects.filter(estafette=e)
    e_cases = []
    for ec in ec_list:
        e_cases.append({
            'object': ec,
            'desc': ui_img(ec.description),
            'edits': EDIT_STRING.format(
                name=prefixed_user_name(ec.last_editor),
                time=timezone.localtime(ec.time_last_edit).strftime(DATE_TIME_FORMAT)
                ),
            'hex': encode(ec.id, context['user_session'].encoder)
        })
    context['estafette'] = {
        'object': e,
        'edits': EDIT_STRING.format(
            name=prefixed_user_name(e.last_editor),
            time=timezone.localtime(e.time_last_edit).strftime(DATE_TIME_FORMAT)
            ) + '<span>&thinsp;XYZ</span>',
        'hex': encode(e.id, context['user_session'].encoder),
        'owner': prefixed_user_name(e.creator),
        'owned': e.creator == context['user'],
        # pass the names and hex IDs of editors
        'editors': [{
            'name': prefixed_user_name(ed),
            'hex': encode(ed.id, context['user_session'].encoder)
            } for ed in e.editors.all()
        ],
        'cases': e_cases
    }

    # add hex IDs of all users having instructor role (except course manager)
    i_role = Role.objects.get(name='Instructor')
    context['staff'] = [{
        'name': prefixed_user_name(p.user),
        'hex': encode(p.user.id, context['user_session'].encoder)
        } for p in Profile.objects.filter(roles__in=[i_role]).exclude(user=context['user'])]

    # show the estafette page
    context['max_file_size'] = settings.MAX_UPLOAD_SIZE
    context['page_title'] = 'Presto Relay' 
    return render(request, 'presto/estafette_view.html', context)


