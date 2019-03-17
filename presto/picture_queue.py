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
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from wsgiref.util import FileWrapper

from .models import Course, CourseStudent, QueuePicture

# python modules
from datetime import datetime, timedelta
from dateutil.tz import tzutc
import email
import mimetypes
import os
import poplib
import re

# presto modules
from presto.generic import change_role, generic_context, report_error, warn_user
from presto.utils import (day_code, decode, encode, log_message, prefixed_user_name,
    string_to_datetime, DATE_FORMAT)

# NOTE: Rotating hex keys would make that images get new URLs each time the view is refreshed.
#       To preserve browser cache efficiency, we use this "key" to generate date-dependent
#       hex keys for pictures. These keys "expire" only once per day (at midnight).
PQ_DAY_CODE = 'Picture Queue'

# view for picture queue page
@login_required(login_url=settings.LOGIN_URL)
def picture_queue(request, **kwargs):
    h = kwargs.get('hex', '')
    act = kwargs.get('action', '')
    # check whether user can view this course
    try:
        if act in ['delete', 'get']:
            # NOTE: when getting a picture, the coding keys should NOT be rotated
            context = generic_context(request, 'NOT')
            # and the day code should be used to decode the hexed queue picture ID
            qpid = decode(h, day_code(PQ_DAY_CODE))
            qp = QueuePicture.objects.get(pk=qpid)
            c = qp.course
        else:
            # the hex code should be a course ID, and key rotation should proceed as usual
            context = generic_context(request, h)
            cid = decode(h, context['user_session'].decoder)
            c = Course.objects.get(pk=cid)
        # always ensure that the user is instructor in the course
        if not (c.manager == context['user'] or c.instructors.filter(id=context['user'].id)):
            log_message('ACCESS DENIED: Invalid course parameter', context['user'])
            return render(request, 'presto/forbidden.html', context)
    except Exception, e:
        report_error(context, e)
        return render(request, 'presto/error.html', context)

    # if queue picture is to be deleted, try to do this
    if act == 'delete':
        try:
            old_path = qp.picture.path
            qp.delete()
            os.remove(old_path)
        except Exception, e:
            warn_user(context, 'Failed to delete queue picture', 'System status: ' + str(e[0]))
    # if queue picture is to be displayed, push its image file to the browser
    elif act == 'get':
        p = qp.picture
        ext = os.path.splitext(p.name)[1]
        # NOTE: mime dict may need to be extended
        mime = {
            '.jpg': 'jpeg',
            '.png': 'png',
        }
        w = FileWrapper(file(p.path, 'rb'))
        return HttpResponse(w, 'image/' + mime.get(ext, '*'))

    # check mail server for new pictures for this course
    try:
        mailbox = poplib.POP3(settings.PICTURE_QUEUE_SERVER)
        mailbox.user(settings.PICTURE_QUEUE_MAIL)
        mailbox.pass_(settings.PICTURE_QUEUE_PWD)
        msg_count = len(mailbox.list()[1])
        log_message('Picture queue found %d message(s) in pq mailbox' % msg_count, context['user'])
        for i in range(msg_count):
            response, msg_as_list, size = mailbox.retr(i + 1)
            msg = email.message_from_string('\r\n'.join(msg_as_list))
            sender = email.utils.parseaddr(msg['From'].strip())
            subject = msg['Subject'].strip()
            # convert the Received field to a timezone-aware datetime object
            received = msg['Received'].split(';')
            t = email.utils.parsedate_tz(received[-1].strip())
            time_received = timezone.localtime(datetime(*t[0:6], tzinfo=tzutc()))
            # see if any course matches the course code from the subject
            if subject:
                c_code = Course.objects.filter(code__iexact=subject)
                if c_code:
                    c_code = c_code.first().code
            else:
                c_code = ''
            # delete any message not having both a valid course code and a time stamp,
            # as well as any message older than 24 hours
            if not (c_code and time_received) or (timezone.now() - time_received).days >= 1:
                log_message('Deleting picture queue message #%d (invalid course code "%s" or too old)' %
                    (i + 1, c_code), context['user'])
                mailbox.dele(i + 1)
            # NOTE: only process messages having a subject that starts with this course's code;
            #       other messages may pertain to other courses and hence should not be deleted
            elif c_code == c.code:
                # determine whether sender is student in this course
                is_student = CourseStudent.objects.filter(user__email__iexact=sender[1],
                        course__code__iexact=c_code).count() > 0
                # if queue is closed, or "strict" while not a course student, delete the message
                if not c.picture_queue_open or (c.picture_queue_strict and not is_student):
                    log_message('Deleting picture queue message #%d from %s' %
                        (i + 1, sender[1]), context['user'])
                    mailbox.dele(i + 1)
                else:
                    # process the message content
                    log_message('Processing picture queue message #%d' % (i + 1), context['user'])
                    try:
                        process_attachment(msg, c, time_received, sender, subject)
                        # only delete the message if processing was successful
                        # NOTE: if problem persists, message will be deleted after 24 hours
                        log_message('Success - message #%d can be deleted' % (i + 1), context['user'])
                        mailbox.dele(i + 1)
                    except Exception, e:
                        log_message('FAILURE -- error message: ' + str(e), context['user'])
        # close mailbox connection -- marked messages will now be deleted
        mailbox.quit()
    except Exception, e:
        warn_user(context, 'Error while retrieving mail', 'System message: ' + str(e))

    # add picture queue mail address
    context['pq_mail'] = settings.PICTURE_QUEUE_MAIL
    
    # add course data to context
    context['course'] = {
        'object': c,
        'hex':  encode(c.id, context['user_session'].encoder),
        'start': c.language.fdate(c.start_date),
        'end': c.language.fdate(c.end_date),
        'manager': prefixed_user_name(c.manager),                         
        'instructors': ', '.join([prefixed_user_name(i) for i in c.instructors.all()])
    }

    # add list of queue pictures for this course
    context['pictures'] = [{
        'object': qp,
        'hex': encode(qp.id, day_code(PQ_DAY_CODE), True), # NOTE: deterministic encoding!
        'time_received': qp.time_received.strftime('%H:%M'),
        'sender': qp.mail_from_name if qp.mail_from_name else qp.mail_from_address
        } for qp in QueuePicture.objects.filter(course=c).order_by('time_received', 'id')
    ]
    context['page_title'] = 'Presto Picture Queue' 
    return render(request, 'presto/picture_queue.html', context)


# auxiliary function: saves message content as QueuePicture if appropriate
def process_attachment(msg, crs, rcvd, sndr, subj):
    # first get the message body text
    body = ''
    for part in msg.walk():
        # multipart/* are just containers
        if part.get_content_maintype() == 'multipart':
            continue
        filename = part.get_filename()
        # body parts have no file name
        if not filename:
            data = part.get_payload(decode=True)
            ext = mimetypes.guess_extension(part.get_content_type())
            if ext == '.txt':
                body += data
            elif ext == '.html':
                # strip all HTML tags
                body += re.sub(r'<.*?>', '', data)
    # then process the attached images
    for part in msg.walk():
        # again skip the multipart/* containers
        if part.get_content_maintype() == 'multipart':
            continue
        filename = part.get_filename()
        if filename:
            rest, ext = os.path.splitext(filename)
            # only accept JPEG and PNG images
            if ext.lower() in ['.jpg', '.jpeg', '.png']:
                qp = QueuePicture(course=crs, time_received=rcvd, mail_from_name=sndr[0],
                    mail_from_address=sndr[1], mail_subject=subj, mail_body=body)
                qp.picture.save(filename, ContentFile(part.get_payload(decode=True), filename))
                qp.save()

