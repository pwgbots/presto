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

from .models import Course, CourseStudent

# python modules
from datetime import datetime

# presto modules
from presto.generic import (
    change_role,
    generic_context,
    has_role,
    inform_user, is_demo_user,
    warn_user
    )
from presto.utils import DATE_TIME_FORMAT, decode, encode


# view for enrollment page (for students)
@login_required(login_url=settings.LOGIN_URL)
def enroll(request, **kwargs):
    context = generic_context(request)
    # check whether user can have student role
    if not change_role(context, 'Student'):
        return render(request, 'presto/forbidden.html', context)
    # check whether user is enrolling
    cc = kwargs.get('course', '')
    cl = Course.objects.filter(code=cc)
    if not cl:
        warn_user(
            context,
            'Unknown course',
            'Course code "<tt>{}</tt>" is not recognized.'.format(cc)
                + 'Please check with your faculty staff.'
            )            
    elif cl.first().is_hidden:
        warn_user(
            context,
            'Unknown course',
            'Course {} is not open for enrollment.'.format(cl.first().title)
            )
    else:
        c = cl.first()
        context['course'] = {
            'object': c,
            'hex': encode(c.id, context['user_session'].encoder)
            }
        # switch to the course language
        context['lang'] = c.language
        csl = CourseStudent.objects.filter(user=context['user'], course=c)
        if csl and not (has_role(context, 'Instructor') or is_demo_user(context)):
            warn_user(
                context,
                c.language.phrase('Already_enrolled'),
                c.language.phrase('Enrolled_on').format(
                    course=c.title(),
                    time=c.language.ftime(csl.first().time_enrolled)
                    )
                )
        else:
            context['enroll'] = c.language.phrase('About_to_enroll').format(
                course=c.title()
                )

    context['page_title'] = 'Presto Enrollment' 
    return render(request, 'presto/enroll.html', context)
