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
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from wsgiref.util import FileWrapper

from .models import (
    Appeal, Assignment,
    Course, CourseEstafette, CourseStudent,
    DEFAULT_DATE,
    EstafetteCase, EstafetteLeg,
    Participant, ParticipantUpload, PeerReview,
    UserDownload
)

# python modules
from docx import Document
import os
from pptx import Presentation
from PyPDF2 import PdfFileWriter, PdfFileReader
from PyPDF2.generic import createStringObject, NameObject
import re
from shutil import copy2, copyfile, make_archive, rmtree
from tempfile import mkstemp
from xml.etree import ElementTree
from zipfile import ZipFile, ZIP_DEFLATED

# presto modules
from presto.generic import change_role, generic_context, has_role, report_error
from presto.utils import (decode, encode, log_message, os_path, random_hex,
    DATE_TIME_FORMAT, EDIT_STRING)


# view for download page
# NOTE: this view does not render a page, but sends a file to the browser
@login_required(login_url=settings.LOGIN_URL)
def download(request, **kwargs):
    # NOTE: downloading a file opens a NEW browser tab/window, meaning that
    # the coding keys should NOT be rotated; this is achieved by passing "NOT" as test code.
    context = generic_context(request, 'NOT')
    # check whether user can have student or instructor role
    is_instructor = has_role(context, 'Instructor')
    if not (has_role(context, 'Student') or is_instructor):
        return render(request, 'presto/forbidden.html', context)
    try:
        h = kwargs.get('hex', '')
        # verify hex key
        # NOTE: since keys have not been rotated, use the ENcoder here!
        aid = decode(h, context['user_session'].encoder)
        file_name = kwargs.get('file_name', '')
        # file_name = 'case' indicates a download request for a case attachment
        if file_name == 'case':
            ec = EstafetteCase.objects.get(pk=aid)
            if ec.upload == None:
                raise ValueError('No attachment file for this case')
            f = ec.upload.upload_file
            ext = os.path.splitext(f.name)[1]
            w = FileWrapper(file(f.path, 'rb'))
            response = HttpResponse(w, 'application/octet-stream')
            response['Content-Disposition'] = (
                'attachment; filename="attachment-case-%s%s"' % (ec.letter, ext))
            return response

        # no case attachment? then the download request must concern an assignment
        work = kwargs.get('work', '')
        dwnldr = kwargs.get('dwnldr', '')
        # verify that download is for an existing assignment
        log_message('Looking for assignment #%d' % aid, context['user'])
        a = Assignment.objects.get(pk=aid)
        
        # get the list of participant uploads for this assignment (or its clone original)
        # and also the full path to the upload directory
        if a.clone_of:
            original = a.clone_of
            # in case a clone was cloned, keep looking until the "true" original has been found
            while original.clone_of:
                original = original.clone_of
            pul = ParticipantUpload.objects.filter(assignment=original)
            upl_dir = os.path.join(settings.MEDIA_ROOT, original.participant.upload_dir)
        else:
            pul = ParticipantUpload.objects.filter(assignment=a)
            upl_dir = os.path.join(settings.MEDIA_ROOT, a.participant.upload_dir)
        log_message('Upload dir = ' + upl_dir, context['user'])
        # create an empty temporary dir to hold copies of uploaded files 
        temp_dir = os.path.join(upl_dir, 'temp')
        try:
            rmtree(temp_dir)
        except:
            pass
        os.mkdir(temp_dir)
        log_message('TEMP dir: ' + temp_dir, context['user'])
        if file_name == 'all-zipped':
            pr_work = 'pr-step%d%s' % (a.leg.number, a.case.letter)
            zip_dir = os.path.join(temp_dir, pr_work)
            os.mkdir(zip_dir)
            # copy the upladed files to the temporary dir ...
            for pu in pul:
                real_name = os.path.join(upl_dir, os.path.basename(pu.upload_file.name))
                # ... under their formal name, not their actual
                ext = os.path.splitext(pu.upload_file.name)[1].lower()
                formal_name = os_path(os.path.join(zip_dir, pu.file_name) + ext)
                if is_instructor:
                    log_message('Copying %s "as is" to ZIP as %s' % (real_name, formal_name), context['user'])
                    # NOTE: for instructors, do NOT anonymize the document
                    copy2(real_name, formal_name)
                else:
                    log_message('Copy-cleaning %s to ZIP as %s' % (real_name, formal_name), context['user'])
                    # strip author data from file and write it to the "work" dir
                    clear_metadata(real_name, formal_name)
            # compress the files into a single zip file
            zip_file = make_archive(zip_dir,'zip', temp_dir, pr_work)
            response = HttpResponse(FileWrapper(file(zip_file,'rb')),
                                    content_type='application/zip')
            response['Content-Disposition'] = (
                'attachment; filename="%s.zip"' % pr_work)
            # always record download in database
            UserDownload.objects.create(user=context['user_session'].user, assignment=a)
            # only change time_first_download if it concerns a predecessor's work!
            if work == 'pre' and a.time_first_download == DEFAULT_DATE:
                a.time_first_download = timezone.now()
            a.time_last_download = timezone.now()
            a.save()
            return response
        else:
            # check whether file name is on "required files" list
            fl = a.leg.file_list()
            rf = False
            for f in fl:
                if f['name'] == file_name:
                    rf = f
            if not rf:
                raise ValueError('Unknown file name: %s' % file_name)
            # find the corresponding upload
            pul = pul.filter(file_name=rf['name'])
            if not pul:
                raise ValueError('File "%s" not found' % rf['name'])
            pu = pul.first()
            # the real file name should not be known to the user
            real_name = os.path.join(upl_dir, os.path.basename(pu.upload_file.name))
            ext = os.path.splitext(pu.upload_file.name)[1]
            # the formal name is the requested file field plus the document's extension
            formal_name = os_path(os.path.join(temp_dir, pu.file_name) + ext)
            if is_instructor:
                log_message('Copying %s "as is" to ZIP as %s' % (real_name, formal_name), context['user'])
                # NOTE: for instructors, do NOT anonymize the document
                copy2(real_name, formal_name)
            else:
                # strip author data from the file
                log_message('Copy-cleaning %s to %s' % (real_name, formal_name), context['user'])
                clear_metadata(real_name, formal_name)
            mime = {
                '.pdf': 'application/pdf',
                '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
            }
            w = FileWrapper(file(settings.LEADING_SLASH + formal_name, 'rb'))
            response = HttpResponse(w, content_type=mime[ext])
            response['Content-Disposition'] = (
                'attachment; filename="%s-%d%s%s"' % (file_name, a.leg.number, a.case.letter, ext))
            # always record download in database
            UserDownload.objects.create(user=context['user_session'].user, assignment=a)
            # only change time_first_download if it concerns a predecessor's work!
            if work == 'pre' and a.time_first_download == DEFAULT_DATE:
                a.time_first_download = timezone.now()
            a.time_last_download = timezone.now()
            a.save()
            # if work is downloaded for the first time by a referee, this should be registered
            if dwnldr == 'ref':
                ap = Appeal.objects.filter(review__assignment=a).first()
                if not ap:
                    raise ValueError('Appeal not found')
                if ap.time_first_viewed == DEFAULT_DATE:
                    ap.time_first_viewed = timezone.now()
                    ap.save()
                    log_message('First view by referee: ' + unicode(ap), context['user'])
            return response
            
    except Exception, e:
        report_error(context, e)
        return render(request, 'presto/error.html', context)


# auxiliary function: removes language tags from XML files in the ZIP file
def clean_xml_in_zip(zip_name):
    # construct a list (name, data) for all XML files in the ZIP
    xml_list = []
    xml_names = []
    zf = ZipFile(zip_name, 'r')
    zl = zf.infolist()
    word_re = re.compile(ur'<w:lang( w:[a-zA-Z]{1,16}="[a-zA-Z\-]{1,10}"){1,5}/>', re.UNICODE)
    ppt_re = re.compile(ur' lang="[a-zA-Z\-]{1,10}"', re.UNICODE)
    for x in zl:
        if x.filename[-4:] == '.xml':
            xml_names.append(x.filename)
            xml = zf.open(x, 'rU').read().decode('utf-8')
            # MS Word: completely remove tags with language codes
            xml = word_re.sub('', xml)
            # MS PowerPoint: strip language attribute from tags with language codes
            xml = ppt_re.sub('', xml)
            xml_list.append((x.filename, xml.encode('utf-8')))
    zf.close()
    # create a temporary file
    tmp_fd, tmp_name = mkstemp(dir=os.path.dirname(zip_name))
    os.close(tmp_fd)
    # create a copy of the archive without XML files
    with ZipFile(zip_name, 'r') as src_zip:
        with ZipFile(tmp_name, 'w') as dst_zip:
            dst_zip.comment = src_zip.comment # preserve the comment (if any)
            for item in src_zip.infolist():
                if not (item.filename in xml_names):
                    dst_zip.writestr(item, src_zip.read(item.filename))
    # replace the original with the temporary archive
    os.remove(zip_name)
    os.rename(tmp_name, zip_name)
    # add XML files with their new data
    with ZipFile(zip_name, mode='a', compression=ZIP_DEFLATED) as zf:
        for x in xml_list:
            zf.writestr(x[0], x[1])


# auxiliary function: reads document src, removes metadata, and writes it to dst
# NOTE: works only for .docx, .pptx and .pdf and now also .xlsx
# NOTE: catches all exceptions; logs them without user name
def clear_metadata(src, dst):
    src = settings.LEADING_SLASH + src
    dst = settings.LEADING_SLASH + dst
    ext = os.path.splitext(dst)[1]  # assumed to be in lower case!
    meta_fields= ['author', 'category', 'comments', 'content_status',
                  'identifier', 'keywords', 'last_modified_by',
                  'language', 'subject', 'title', 'version']
    try:
        if ext in ['.docx']:
            f = open(src, 'rb')
            doc = Document(f)
            f.close()
            for meta_field in meta_fields:
                setattr(doc.core_properties, meta_field, '')
            setattr(doc.core_properties, 'created', DEFAULT_DATE)
            setattr(doc.core_properties, 'modified', DEFAULT_DATE)
            setattr(doc.core_properties, 'last_printed', DEFAULT_DATE)
            setattr(doc.core_properties, 'revision', 1)
            doc.save(dst)
            clean_xml_in_zip(dst)
        elif ext in ['.pptx']:
            prs = Presentation(src)
            for meta_field in meta_fields:
                setattr(prs.core_properties, meta_field, '')
            setattr(prs.core_properties, 'created', DEFAULT_DATE)
            setattr(prs.core_properties, 'modified', DEFAULT_DATE)
            setattr(prs.core_properties, 'last_printed', DEFAULT_DATE)
            setattr(prs.core_properties, 'revision', 1)
            prs.save(dst)
            clean_xml_in_zip(dst)
        elif ext == '.pdf':
            fin = file(src, 'rb')
            inp = PdfFileReader(fin)
            outp = PdfFileWriter()
            for page in range(inp.getNumPages()):
                outp.addPage(inp.getPage(page))
            infoDict = outp._info.getObject()
            infoDict.update({
                NameObject('/Title'): createStringObject(u''),
                NameObject('/Author'): createStringObject(u''),
                NameObject('/Subject'): createStringObject(u''),
                NameObject('/Creator'): createStringObject(u'')
            })
            fout = open(dst, 'wb')
            outp.write(fout)
            fin.close()
            fout.close()
        elif ext == '.xlsx':
            file_to_clear = 'docProps/core.xml'
            # create a copy of the Excel file while "cleaning" docProps/core.xml
            with ZipFile(src, 'r') as src_zip:
                with ZipFile(dst, 'w') as dst_zip:
                    dst_zip.comment = src_zip.comment # preserve the comment (if any)
                    for item in src_zip.infolist():
                        if item.filename == file_to_clear:
                            # read the XML tree from the file
                            xml = src_zip.read(item.filename)
                            xml = re.sub(r'<dc:title>[^<]{1,1000}</dc:title>', '<dc:title></dc:title>', xml)
                            xml = re.sub(r'<dc:subject>[^<]{1,500}</dc:subject>', '<dc:subject></dc:subject>', xml)
                            xml = re.sub(r'<dc:creator>[^<]{1,300}</dc:creator>', '<dc:creator></dc:creator>', xml)
                            xml = re.sub(r'<dc:description>[^<]{1,2500}</dc:description>', '<dc:description></dc:description>', xml)
                            xml = re.sub(r'<cp:keywords>[^<]{1,1000}</cp:keywords>', '<cp:keywords></cp:keywords>', xml)
                            xml = re.sub(r'<cp:lastModifiedBy>[^<]{1,300}</cp:lastModifiedBy>', '<cp:lastModifiedBy></cp:lastModifiedBy>', xml)
                            xml = re.sub(r'<cp:category>[^<]{1,300}</cp:category>', '<cp:category></cp:category>', xml)
                            xml = re.sub(r'<cp:contentStatus>[^<]{1,100}</cp:contentStatus>', '<cp:contentStatus></cp:contentStatus>', xml)
                            xml = re.sub(r'<cp:revision>[^<]{1,10}</cp:revision>', '<cp:revision></cp:revision', xml)
                            # replace all date-time fields with the default date
                            xml = re.sub(r':W3CDTF">[^<]{1,25}</dcterms:', ':W3CDTF">2001-01-01T00:00:00Z</dcterms:', xml)
                            dst_zip.writestr(item, xml)
                        else:
                            dst_zip.writestr(item, src_zip.read(item.filename))
    except Exception, e:
        log_message('Exception while removing metadata from a %s file: %s'
                    % (ext, str(e)))
    return
