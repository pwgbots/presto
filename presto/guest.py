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
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

# presto modules
from presto.generic import (authenticated_user, decode, encode, generic_context,
     warn_user)
from presto.student import student

# Python modules
from hashlib import md5
from re import match

# Guest list (md5 hash of username|password)
GUEST_LIST = {
    'mtermaat': 'fb51070f210a08d1ab5cf80ffd224fe8',
}

# no login required for guest users w/o NetID; merely prompt for user name and password
def guest(request):
    context = generic_context(request)
    context['page_title'] = 'Presto guest login' 
    return render(request, 'presto/guest.html', context)

# guest users are authenticated by a hashed password
@method_decorator(csrf_exempt, name='dispatch')
def guest_login(request):
    context = generic_context(request)
    context['page_title'] = 'Presto guest login'
    nid = request.POST.get('netid', '').strip().lower()
    pwd = request.POST.get('passw', '').strip()
    hex = md5(nid + '|' + pwd).hexdigest()
    # see if username and password match
    if GUEST_LIST.get(nid, '') == hex:
        # see if nid identifies a user
        try:
            usr = User.objects.get(username=nid)
        except:
            return render(request, 'presto/forbidden.html', context)
        # guest login similar to demo user login
        usr.backend = settings.DEMO_USR_BACKEND
        login(request, usr)
        context = generic_context(request)
        return student(request)

    # if no match, notify the user and show the initial guest login dialog
    warn_user(context, 'Invalid guest credentials', 'Please try again.', 
        'Guest not authenticated: ' + '|'.join([nid, pwd, hex]))
    return render(request, 'presto/guest.html', context)

