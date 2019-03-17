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

#

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

# presto modules
from presto.generic import (authenticated_user, decode, encode, generic_context,
    set_focus_and_alias, validate_alias, warn_user)
from presto.student import student

from .models import Course, CourseEstafette, CourseStudent

# Python modules
from hashlib import md5
from re import match


# no login required for demo participants; merely prompt for alias and demonstration code
def demo(request):
    context = generic_context(request)
    context['page_title'] = 'Presto demonstration' 
    return render(request, 'presto/demo.html', context)

# no login required for demo participants, as they are authenticated by a hashed
# login code that identifies an active demonstration course estafette.
# NOTE: users are logged in as the (one-and-only!) demo user, prompted to enter their
#       first name, and then made into a "focused" participant
@method_decorator(csrf_exempt, name='dispatch')
def demo_login(request):
    context = generic_context(request)
    context['page_title'] = 'Presto demonstration'
    # define two *deterministic* 32 hex digit keys to encode/decode the ID parameters
    de_key = md5(context['page_title']).hexdigest()
    ds_key = md5(de_key).hexdigest()
    # if PIN is passed, hex is the encoded ID
    pin = request.POST.get('pin', '').strip().upper()
    h = request.POST.get('hex', '').strip()
    if pin and h:
        de_hex = h[:32]
        ds_hex = h[-32:]
        # see if hex encodes a course student ID
        try:
            ds = CourseStudent.objects.get(id=decode(ds_hex, ds_key))
        except:
            return render(request, 'presto/forbidden.html', context)
        # if student PIN matches the one entered in the PIN dialog, focus on this participant
        # and show the student view
        if pin == ds.pin():
            # log in as the (one-and-only!) demo user
            usr = User.objects.get(username=settings.DEMO_USER_NAME)
            usr.backend = settings.DEMO_USR_BACKEND
            login(request, usr)
            context = generic_context(request)
            # pass "clear_sessions" = True so that old "focused" user session record is deleted
            set_focus_and_alias(context, ds.id, ds.particulars, True)
            return student(request)
        # if not, notify the user and show the initial demo dialog
        warn_user(context, 'Invalid PIN', 'Please try again, or cancel to log in with a different alias.')
        try:
            de = CourseEstafette.objects.get(id=decode(de_hex, de_key))
        except:
            return render(request, 'presto/forbidden.html', context)
        context['estafette'] = de.title
        context['de_hex'] = de_hex
        context['ds_hex'] = encode(ds.id, ds_key)
        return render(request, 'presto/demo.html', context)
        
    # no PIN? then expect an alias and a code
    b36 = request.POST.get('code', '').strip()
    alias = request.POST.get('alias', '').strip()
    # warn user if alias is invalid
    if not validate_alias(context, alias):
        return render(request, 'presto/demo.html', context)

    # validate this code as a "running" DEMO course estafette id
    demo_courses = Course.objects.filter(code='DEMO')
    if demo_courses:
        # only get the active estafettes for the DEMO course
        demo_estafettes = CourseEstafette.objects.filter(course__id__in=demo_courses
            ).exclude(start_time__gte=timezone.now()).exclude(end_time__lte=timezone.now())
        if demo_estafettes:
            for de in demo_estafettes:
                if b36 == de.demonstration_code():
                    # get the demonstration user
                    usr = User.objects.get(username=settings.DEMO_USER_NAME)
                    # get the highest dummy index for this course
                    dsl = CourseStudent.objects.filter(user=usr, course=de.course, dummy_index__gt=0)
                    if dsl:
                        hdi = max([ds.dummy_index for ds in dsl])
                    else:
                        hdi = 0
                    # see if alias matches any "dummy" course student
                    ds = dsl.filter(particulars=alias).first()
                    if ds:
                        # existing user? then ask for PIN
                        context['estafette'] = de.title
                        context['de_hex'] = encode(de.id, de_key)
                        context['ds_hex'] = encode(ds.id, ds_key)
                    else:
                        # create new "dummy" course student
                        ds = CourseStudent(course=de.course, user=usr,
                            dummy_index=hdi + 1, particulars=alias,
                            time_enrolled=timezone.now(), last_action=timezone.now())
                        ds.save()
                        # log in as the (one-and-only!) demo user
                        usr.backend = settings.DEMO_USR_BACKEND
                        login(request, usr)
                        context = generic_context(request)
                        # create a *deterministic* PIN based on the user's alias and dummy index
                        context['pin'] = ds.pin()
                        context['alias'] = ds.particulars
                        # focus on this "dummy" student
                        set_focus_and_alias(context, ds.id, ds.particulars)
                    # show the demo dialog
                    return render(request, 'presto/demo.html', context)
            # FALL-THROUGH: matching estafette
            warn_user(context, 'Invalid code',
                'The code you entered does not identify a demonstration relay.')
        else:
            warn_user(context, 'No demonstration relay',
                'Presently, no demonstration relays are open for enrollment.')
    else:
        warn_user(context, 'No demonstration course',
            '<em>Note:</em> Demonstration courses must have code DEMO.')
    if alias == '':
        warn_user(context, 'Alias required',
            'Please provide a name that will identify you as a demonstration user.<br>' +
            '<em>This name must start with a letter and be at least 6 characters long.</em>')
    return render(request, 'presto/demo.html', context)

