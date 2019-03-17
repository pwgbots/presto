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
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.decorators import method_decorator

# presto modules
from presto.ack_letter import ack_letter
from presto.awards import awards
from presto.administrator import administrator
from presto.ajax import ajax
from presto.badge import badge
from presto.course import course
from presto.course_estafette import course_estafette
from presto.demo import demo, demo_login
from presto.developer import developer
from presto.download import download
from presto.enroll import enroll
from presto.estafette_view import estafette_view
from presto.generic import decode, generic_context, has_role, report_error
from presto.history_view import history_view, set_history_properties
from presto.instructor import instructor
from presto.picture_queue import picture_queue
from presto.plag_scan import scan_one_assignment
from presto.progress import progress
from presto.student import student
from presto.template import template
from presto.test_file_type import test_file_type
from presto.utils import log_message
from presto.verify import verify

from .models import DEFAULT_DATE, Assignment, Participant, ParticipantUpload

import codecs
import os
import re
import tempfile
from urllib import unquote
import zipfile

@login_required(login_url=settings.LOGIN_URL)
def index(request):
    context = generic_context(request)
    r = context['user_session'].active_role
    if r:
        if r.name == 'Student':
            return student(request)
        elif r.name == 'Instructor':
            return instructor(request)
        elif r.name == 'Developer':
            return developer(request)
        elif r.name == 'Administrator':
            return administrator(request)
    else:
        return render(request, 'presto/index.html', context)


@login_required(login_url=settings.LOGIN_URL)
def announcements(request):
    context = generic_context(request)
    context['page_title'] = 'Presto Announcements' 
    return render(request, 'presto/announcements.html', context)


@login_required(login_url=settings.LOGIN_URL)
def setting_view(request):
    context = generic_context(request)
    context['page_title'] = 'Presto Settings' 
    return render(request, 'presto/setting_view.html', context)


# returns contents of Presto log file (plain text)
@login_required(login_url=settings.LOGIN_URL)
def log_file(request, **kwargs):
    ymd = kwargs.get('date', '')
    if ymd == '':
        ymd = timezone.now().strftime('%Y%m%d')
    context = generic_context(request)
    try:
        log_message('Viewing log file %s' % ymd, context['user'])
        if not has_role(context, 'Administrator'):
            raise IOError('No permission to view log files')
        path = os.path.join(settings.LOG_DIR, 'presto-%s.log' % ymd)
        with codecs.open(path, 'r', encoding='utf8') as log:
            content = log.read()
            lines = kwargs.get('lines', '')
            pattern = unquote(kwargs.get('pattern', '')).decode('utf8') 
            if lines:
                # show last N lines
                content = '\n'.join(content.split('\n')[int(lines):])
            elif pattern:
                # show pattern-matching lines, separated by blank line
                content = '\n\n'.join(re.findall('^.*' + pattern + '.*$', content, re.MULTILINE))
    except IOError, e:
        report_error(context, e) 
        return render(request, 'presto/error.html', context)
    return HttpResponse(content, content_type='text/plain; charset=utf-8')


@login_required(login_url=settings.LOGIN_URL)
def dataset(request, **kwargs):
    h = kwargs.get('hex', '')
    context = generic_context(request, h)
    try:
        if not has_role(context, 'Administrator'):
            raise IOError('No permission to download relay data set')
        context['page_title'] = 'Presto Relay Dataset'
        context['no_names'] = True
        context['identify'] = True
        ceid = decode(h, context['user_session'].decoder)
        # get all relay participants except dummy students
        p_set = Participant.objects.filter(estafette__id=ceid, student__dummy_index=0)
        # create list of ID - e-mail address
        data = '\n'.join(['#(%d)\t%s' % (v[0], v[1])
            for v in p_set.values_list('id', 'student__user__email')])
        # make a temporary zip file
        with tempfile.SpooledTemporaryFile() as tmp:
            with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # add a text file with (id - e-mail address) for each participant
                zip_file.writestr('participants.txt', data.encode('utf-8'))
                for p in p_set:
                    # add data for progress bar
                    context['things_to_do'] = p.things_to_do()
                    # NOTE: context properties will include identities of participants
                    set_history_properties(context, p)
                    context['object'] = p
                    context['base_url'] = '.'
                    data = render_to_string('estafette_history.html', context)
                    data = data.replace('/static/presto', 'presto')
                    zip_file.writestr('p%d.html' % p.id, data.encode('utf-8'))
            # reset file pointer
            tmp.seek(0)
            response = HttpResponse(tmp.read(), content_type='application/zip')
            response['Content-Disposition'] = 'attachment; filename="relay_dataset.zip"'
            return response

    except IOError, e:
        report_error(context, e) 
        return render(request, 'presto/error.html', context)


# perform plagiarism scan on one assignment (if any)
# NOTE: this view is to be called from a CRON job
def scan(request, **kwargs):
    content = 'One scan completed'
    try:
        scan_one_assignment()
        # below is a provisionary patch to remedy double assignments
        # NOTE: the uniqueness constraint on Assignment is NOT effectuated because
        #       the "cloneOf" foreign key field can be NULL (a Django-specific issue)
        doubles = Assignment.objects.filter(is_rejected=False, clone_of__isnull=True
            ).values('participant__id', 'leg__id'
            ).annotate(same_leg_cnt=Count('id')
            ).values('participant__id', 'leg__id', 'same_leg_cnt'
            ).order_by().filter(same_leg_cnt__gt=1)
        for d in doubles:
            a_set = Assignment.objects.filter(participant__id=d['participant__id'],
                leg__id=d['leg__id']).order_by('-id')
            # double-check that there is a duplicate assignment
            if len(a_set) > 1:
                # get the latest one
                a = a_set.first()
                # also get the one to keep
                b = a_set[1] 
                # log that we found a duplicate
                log_message('WATCHDOG: Found duplicate assignment #%d-%s%d--%s' %
                    (a.id, a.case.letter, a.leg.number, a.participant.student.dummy_name()))
                log_message('-- original assignment: #%d-%s%d--%s' %
                    (b.id, b.case.letter, b.leg.number, b.participant.student.dummy_name()))
                # also log the name of the relay
                log_message('-- Relay: %s' % a.participant.estafette.title())
                # ensure that there are NO uploads (because these CASCADE delete)
                puc = ParticipantUpload.objects.filter(assignment=a).count()
                if puc > 0:
                    log_message('-- NOT deleted because it has associated uploads')
                else:
                    try:
                        # NOTE: deleting duplicate will set its predecessor's successor field to NULL
                        a.delete()
                        log_message('-- duplicate now deleted')
                        # NOTE: we must now restore predecessor's successor field!!
                        b.predecessor.successor = b
                        b.predecessor.save()
                        log_message('-- predecessor-successor restored')
                    except:
                        # signal that assignment ID is a foreign key of some other record
                        log_message('-- NOT deleted (probably related assignments or reviews)')
                    
    except Exception, e:
        content = 'ERROR during scan: %s' % str(e)
    return HttpResponse(content, content_type='text/plain; charset=utf-8')


# report assignments suspected of plagiarism 
# NOTE: this view is 
def suspect(request, **kwargs):
    h = kwargs.get('hex', '')
    context = generic_context(request, h)
    try:
        if not has_role(context, 'Administrator'):
            raise IOError('No permission to download relay data set')
        context['page_title'] = 'Presto Plagiarism Report'
        ceid = decode(h, context['user_session'].decoder)
        # get all relay assignments (except clones and dummy students) having
        # a scan result of 5% or more, and for steps 3 and above 3% or more
        a_set = Assignment.objects.filter(clone_of__isnull=True,
            participant__estafette__id=ceid, participant__student__dummy_index=0,
            time_scanned__gt=DEFAULT_DATE, scan_result__gte=3
            ).select_related('case', 'leg', 'participant__student'
            ).exclude(leg__number__lte=2, scan_result__lte=5
            ).order_by('case__letter', 'leg__number', 'time_uploaded')
        
        content = '%d suspects\n\n' % len(a_set)
        for a in a_set:
            content += '\n%s%d by %s (#%d, %d%%)' % (a.case.letter, a.leg.number,
                a.participant.student.dummy_name(), a.id, a.scan_result)
            pr_a = a.predecessor
            if pr_a in a_set:
                content += ' -- builds on %s%d by %s (#%d)' % (pr_a.case.letter,
                    pr_a.leg.number, pr_a.participant.student.dummy_name(), pr_a.id)
         

        return HttpResponse(content, content_type='text/plain; charset=utf-8')

    except IOError, e:
        report_error(context, e) 
        return render(request, 'presto/error.html', context)

