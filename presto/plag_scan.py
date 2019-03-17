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
from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone
from django.utils.html import strip_tags 

from .models import Assignment, EstafetteLeg, Participant, ParticipantUpload, DEFAULT_DATE

from presto.utils import log_message

from datetime import datetime
from difflib import SequenceMatcher
from docx import Document
from io import BytesIO, TextIOWrapper
from json import dumps, loads
from markdown import markdown
import os
import time
from subprocess import check_output
from zipfile import ZipFile

# maximum duration of a single scan (to prevent request timeouts)
MAX_SECONDS = 30

# minimum number of characters to be considered a relevant match during text comparison
MATCH_THRESHOLD = 20

# minimum total length of detected matches to be considered as potential plagiarism
TOTAL_MATCH_THRESHOLD = 150

# minimum matching percentage to be considered suspect
SUSPICION_THRESHOLD = 3

# HTML green-to-red color scale to highlight matching percentages
SCAN_STATUS_COLORS = [(0, '#00bb00'), (1, '#a8c818'), (SUSPICION_THRESHOLD, '#d0d000'),
    (10, '#d89818'), (20, '#d85818'), (30, '#d82818'), (40, '#ff0000'),
    (50, '#d80000'), (200, '#a80000'), (1000, '#a80000')]

# HTML to denote scan status with numbered cicles (NOTE: works only up to 10 steps)
OPEN_SCAN_SYMBOL = '<span style="color: %s">&#x278%x;</span>'
SOLID_SCAN_SYMBOL = '<span style="color: %s">&#x278%x;</span>'

# HTML to denote non-matching text left out between matches
BLUE_ELLIPSIS = '<span style="color: #00A6D6"> [...%d...] </span>'

# separator tag for tell-tales added to extracted text from OpenDoc files
TELLTALE_SEPARATOR = '!!--TELL-TALES--!!'

# XML tag for OpenDoc file creation time
TIME_CREATED_TAG = '<dcterms:created xsi:type="dcterms:W3CDTF">'

# typical fragments to ignore while scanning
COMMON_FRAGMENTS = ['https://', 'http://', 'presto.tudelft.nl', 'mod-est.tbm.tudelft.nl',
    'openclipart.org/', 'www.flaticon.com/', 'www.pexels.com/', 'pixabay.com/', 'www.rgbstock.com/',
    'raadpleegd op', 'llustratie]']


# returns a color on a green via orange to red scale to signal high matching percentages
def status_color(perc):
    perc = abs(perc)  # percentages may be negative to signal suspect RELATED matches
    for p, c in SCAN_STATUS_COLORS:
        if perc <= p:
            return c
    return '#000000'  # defaults to black (should occur only when perc is not a number)


# returns HTML denoting a numbered circle in the color corresponding to the match percentage,
# or silver if no percentage is passed
# NOTE: a negative value of perc indicates a suspect match with RELATED work;
#       this is indicated with colored OPEN numbered circles
def step_status(nr, perc=None):
    if perc is None:
        return OPEN_SCAN_SYMBOL % ('silver', nr - 1)
    if perc < 0:
        return OPEN_SCAN_SYMBOL % (status_color(perc), nr - 1)
    return SOLID_SCAN_SYMBOL % (status_color(perc), (nr + 9) % 16)


# retrieves text from:
# - DOCX documents (paragraphs only, so ignoring tables, headers, etc.)
# - a PDF document (using the Unix pdftotext utility --  will not work on Windows platform!)
# and appends some "tell tale" properties from DOCX and XLSX files
def ascii_from_doc(path, text_to_ignore=[]):
    ext = os.path.splitext(path)[1].lower()
    if ext == '.docx':
        f = open(path, 'rb')
        doc = Document(f)
        f.close()
        text = []
        for par in doc.paragraphs:
            # first convert non-breaking spaces to normal ones, and then reduce all whitespace to 1 space
            text.append(' '.join(par.text.replace(unichr(160), ' ').strip().split()))  
        # convert to ASCII to get rid of special chars like curled quotes
        ascii = (' '.join([s for s in text])).encode('ascii', 'ignore')
        for t in text_to_ignore:
            ascii = ascii.replace(t.encode('ascii', 'ignore'), '')
        # NOTE: Word files are also scanned for the images they contain (in xl/media),
        #       and for their creation date (from docProps/core)
        # NOTE: we signal this the start of the "tell-tale list" with a separator
        ascii += TELLTALE_SEPARATOR
        error = ''
        try:
            with ZipFile(path, 'r') as zf:
                # append for each image file a line "<extension>=<file size>+<CRC>" 
                for i in zf.infolist():
                    if i.filename[:11] == 'word/media/':
                        ascii += '\n%s=%d+%d' % (os.path.splitext(i.filename)[1].lower(),
                            i.file_size, i.CRC)
                    elif i.filename == 'docProps/core.xml':
                        try:
                            # try to extract the creation time stamp
                            core = zf.read(i)
                            #log_message('%d bytes read from core' % len(core))
                            p = core.index(TIME_CREATED_TAG) + len(TIME_CREATED_TAG)
                            cdt = core[p:p + 16]
                            # ignore the presto "undefined" date
                            if cdt != '2001-01-01T00:00':
                                ascii += '\ncreated=%s' % cdt
                        except Exception:
                            # ignore any errors while checking core.xml
                            pass

        except Exception, e:
            error = str(e)
        if error:
            log_message('WARNING: Failed to scan file %s as ZIP archive\n%s' % (path, error))
        return ascii
    elif ext == '.pdf':
        ascii = ''
        try:
            # extract text from PDF as 7-bit ASCII (note: this also removes 'hard' spaces)
            ascii = check_output(['pdftotext', '-enc', 'ASCII7', path, '-'])
            # remove sequences of 3+ periods (typically occur in table of contents)
            ascii = ' '.join(ascii.replace('...', '').strip().split())
            # remove text to ignore
            for t in text_to_ignore:
                ascii = ascii.replace(t.encode('ascii', 'ignore'), '')
        except Exception, e:
            log_message('ERROR: Failed to execute pdftotext for file %s\n%s' % (path, str(e)))
        return ascii
    elif ext == '.xlsx':
        # NOTE: Excel files are not scanned for text, but -- similar to Word files -- for the images
        #       they contain (in xl/media), for their shared strings (in xl/sharedStrings.xml),
        #       and for their creation date (from docProps/core)
        # NOTE: we signal this the start of the "tell-tale list" with a separator
        ascii = TELLTALE_SEPARATOR
        error = ''
        try:
            with ZipFile(path, 'r') as zf:
                # append for each image file a line "<extension>=<file size>+<CRC>" 
                for i in zf.infolist():
                    if i.filename[:9] == 'xl/media/':
                        ascii += '\n%s=%d+%d' % (os.path.splitext(i.filename)[1].lower(),
                            i.file_size, i.CRC)
                    elif i.filename == 'docProps/core.xml':
                        try:
                            # try to extract the creation time stamp
                            core = zf.read(i)
                            #log_message('%d bytes read from core' % len(core))
                            p = core.index(TIME_CREATED_TAG) + len(TIME_CREATED_TAG)
                            cdt = core[p:p + 16]
                            # ignore the presto "undefined" date
                            if cdt != '2001-01-01T00:00' and cdt !='2018-11-19T11:54':
                                ascii += '\ncreated=%s' % cdt
                        except Exception:
                            # ignore any errors while checking core.xml
                            pass
        except Exception, e:
            error = str(e)
        if error:
            log_message('WARNING: Failed to scan file %s as ZIP archive\n%s' % (path, error))
        return ascii
    else:
        log_message('File %s is not DOCX, XLSX or PDF and hence not scanned' % path)
        return ''


# returns a tuple (percentage, report) where:
#  percentage: the total length of matching parts in the text file divided by the length
#              of the original text (minus strings in list text_to_ignore) * 100
#  report:     a Markdown-formatted description on size, position, and content of matching
#              text of at least min_length characters
def scan_report(text, req_file, path, aid, author, upload_time, related, min_length, text_to_ignore=[]):
    # NOTE: we also scan for matching "tell-tales"
    tell_tales = ''
    tt_percent = 0
    # test whether a "tell-tale" scan is needed
    if TELLTALE_SEPARATOR in text:
        matches = []
        parts = text.split(TELLTALE_SEPARATOR)
        # separate the text content from the "tell-tale" list
        if len(parts) == 1:
            # text only contained "tell-tales" (typical for .XLSX files)
            text = ''
            pairs = parts[0].strip()
        else:
            text = parts[0].strip()
            pairs = parts[1].strip()
        # check if there are any "tell-tales"
        pairs = pairs.split('\n')
        if len(pairs) == 0:
            tell_tales = '_(No tell-tales in file `%s`)_' % os.path.basename(path)
        else:
           # get the text content from the file to scan
            scan_text = ascii_from_doc(path)
            # return warning report if no "tell-tales" detected
            if TELLTALE_SEPARATOR not in scan_text:
                tell_tales = ('_**WARNING:** File `%s` did not scan as OpenDocument._' %
                    os.path.basename(path))
            else: 
                # parse tell tales (these all have form "key|value")
                parts = scan_text.split(TELLTALE_SEPARATOR)
                # separate the text content from the "tell-tale" list
                if len(parts) == 1:
                    # text only contained "tell-tales" (typical for .XLSX files)
                    scan_text = ''
                    scan_pairs = parts[0].strip()
                else:
                    scan_text = parts[0].strip()
                    scan_pairs = parts[1].strip()
                scan_pairs = scan_pairs.split('\n')
                # collect matching pairs
                for p in scan_pairs:
                    if p and p in pairs:
                        matches.append(p)
        # report matching "tell-tales" (if any)
        if len(matches) > 0:
            tt_percent = int(100 * len(matches) / len(pairs))
            tell_tales = 'Tell-tales: %d%% match (%s)' % (tt_percent, ', '.join(matches))

    # now scan for text matches
    l = len(text)
    # assume no match
    n = 0
    matching_text = ''
    percentage = 0
    epolm = 0  # end position of last match
    if l:
        s = SequenceMatcher(None, text, ascii_from_doc(path, text_to_ignore))
        for match in s.get_matching_blocks():
            if match.size >= min_length:
                n += match.size
                if epolm > 0:
                    matching_text += BLUE_ELLIPSIS % (match.a - epolm)
                epolm = match.a + match.size
                matching_text += text[match.a:match.a + match.size].decode('utf-8')
        # NOTE: matches that are (only a few characters) longer than an ingnorable string
        #       are not ignored; hence we strip "to ignore" text fragments from the report
        mtl = len(matching_text)
        for t in text_to_ignore:
            matching_text = matching_text.replace(t, '')
        # adjust n by subtracting the number of removed characters
        n -= mtl - len(matching_text)

    # report if sufficient matching text or "tell-tales"
    if n > TOTAL_MATCH_THRESHOLD or tt_percent > 0:
        if related:
            author = 'RELATED ' + author
            matching_text = '_(matching text and tell-tales omitted because source is legitimate)_'
            tell_tales = ''
        percentage = int(100 * n / l) if l else 0
        report = ('####%d%% text match (%d characters) with `%s` <small>(submitted on %s by %s as `%s`)</small>\n'
            % (percentage, n, req_file, upload_time, author,
               os.path.basename(path))) + '<small>' + matching_text + '</small>'
        # append "tell-tale" report if matching tell-tales were found
        if tt_percent > 0:
            report += tell_tales
            percentage = max(percentage, tt_percent)
        # NOTE: a very large match (80% or more) with related work may indicate NO own contribution,
        #       hence such submissions are not "cleared" by setting percentage to 0
        if related and percentage < 80:
            # return 0 as percentage, as this match is not to be considered as plagiarism
            percentage = 0
    else:
        report = 'NO text match with `%s` (%s)' % (os.path.basename(path), author)
        if related:
            report += ' _(NOTE: despite being **related** work!)_  '

    # only log suspect scans
    if ((percentage > SUSPICION_THRESHOLD or n > 500) and not related) or percentage >= 80:
        log_message('-- %d%% (%d characters) match with %s submitted on %s by %s (#%d)'
            % (percentage, n, req_file, upload_time, author, aid))
    # indicate matches with related work as a negative percentage
    if related:
        percentage = -percentage   
    return (percentage, report)


# scans the uploaded required files (e.g., "report") for the assignment with ID aid
# returns a tuple (max. match percentage, scan report in HTML format)
def scan_assignment(aid):
    # track time needed for this (partial) scan
    start_time = time.time()
    # get the assignment to be scanned
    a = Assignment.objects.select_related('participant__student').get(pk=aid)
    author = a.participant.student.dummy_name()
    # ignore if no uploaded work or clone
    if a.time_uploaded == DEFAULT_DATE or a.clone_of:
        return (0, '')
    upl_dir = os.path.join(settings.MEDIA_ROOT, a.participant.upload_dir)
    # directory may not exist yet (typically because relay template has no required files)
    if not os.path.exists(upl_dir):
        os.mkdir(upl_dir)
    # prepare to use two text files: one for progress and draft report, one for complete report        
    report_path = os.path.join(upl_dir, 'scan_%s%d.txt' % (a.case.letter, a.leg.number))
    progress_path = os.path.join(upl_dir, 'progress_%s%d.txt' % (a.case.letter, a.leg.number))

    # if database record shows completed scan, check if report exists
    if a.time_scanned != DEFAULT_DATE:
        # if report indeed exists, read it, get the max. percentage, and return its contents
        if os.path.isfile(report_path):
            content = unicode(open(report_path, 'r').read(), errors='ignore')
            return (a.scan_result, markdown(content).replace('<h2>',
                '<h2 style="color: %s">' % status_color(a.scan_result), 1))

    # if progress file exists, resume the scan
    resuming = False
    if os.path.isfile(progress_path):
        try:
            data = loads(unicode(open(progress_path, 'r').read(), errors='ignore'))
            # get time since data was saved
            t_diff = round(time.time() - data['start'])
            # first verify that assignment IDs match
            if data['aid'] != a.id:
                log_message('ERROR: Resuming scan ID mismatch (got #%d while expecting #%d)' % (
                    data['aid'], a.id))
            # resume only if partial scan is less than 15 minutes old AND not busy
            elif t_diff < 900 and not ('busy' in data):
                # restore "legitimate source" ID list from data
                prid_list = data['prids']
                # restore "strings to ignore"
                to_ignore = data['ignore']
                # get min and max percentages
                min_perc = data['min_perc']
                max_perc = data['max_perc']
                # restore scan report list
                fsr = data['fsr']
                fs_cnt = data['fs_cnt']
                # restore "assignments to scan" ID list and record list
                said_list = data['saids']
                sa_dict = {}
                for sa in Assignment.objects.filter(id__in=said_list
                    ).select_related('participant__student'):
                    sa_dict[sa.id] = {'id': sa.id, 'leg': sa.leg.number,
                        'author': sa.participant.student.dummy_name(), 'uploaded': sa.time_uploaded}
                # get the IDs of file uploads already scanned
                spuid_list = data['spuids']
                log_message('Resuming scan of #%d by %s (%d seconds ago; %d scanned)' % (
                    data['aid'], data['author'], t_diff, len(spuid_list)))
                # NOTE: set resuming to TRUE to indicate successful resume
                resuming = True
            else:
                log_message('ABANDONED scan of #%d by %s (%d seconds ago)' % (a.id, author, t_diff))
        except Exception, e:
            # log error and then ignore it
            log_message('WARNING: Ignoring resume failure: %s' % str(e))
    else:
        log_message('Starting scan of #%d by %s' % (a.id, author))

    # if no progress file OR unsuccessful resume, start from scratch
    if not resuming:
        # immediately create a provisionary progress file as "semaphore"
        with open(progress_path, 'w') as f:
            data = {'aid': a.id, 'start': time.time(), 'busy': True}
            f.write(dumps(data))
        # to avoid false positives, compile a list of assignment IDs that are related:
        # (1) get ALL assignments for same case submitted (until now) by same participant
        #     because it can occur that participants are assigned the same case in several steps
        #     and then decide to reuse their own prior material
        o_set = Assignment.objects.filter(participant=a.participant, case__letter=a.case.letter
            ).filter(time_uploaded__lte=a.time_uploaded)
        # (2) for these assignments, get the consecutive predecessors up to step 1,
        #     tracing cloned work to its original
        prid_list = []
        for o in o_set:
            pr_a = o.predecessor
            while pr_a:
                # in case a clone was cloned, keep looking until the "true" original has been found
                while pr_a.clone_of:
                    pr_a = pr_a.clone_of
                prid_list.append(pr_a.id)
                pr_a = pr_a.predecessor
        # (3) also get all clones of these assignments
        c_list = Assignment.objects.filter(clone_of__in=prid_list).values_list('id', flat=True)
        preds_and_clones = '-- predecessor IDs: %s; clone IDs: %s' % (
            ', '.join([str(i) for i in prid_list]), ', '.join([str(i) for i in list(c_list)]))
        log_message(preds_and_clones)
        prid_list += c_list
        # (4) keep collecting IDs of successor assignments and clones of the "predecessors" found
        #     (one generation at a time) until no more are found
        n_set = set()
        o_set = set(Assignment.objects.filter(Q(predecessor__in=prid_list) | Q(clone_of__in=prid_list)
            ).values_list('id', flat=True)) - n_set
        while o_set:
            n_set = n_set | o_set
            o_set = set(Assignment.objects.filter(Q(predecessor__in=o_set) | Q(clone_of__in=o_set)
                ).values_list('id', flat=True)) - n_set
        offspring = '-- offspring IDs: %s' % ', '.join([str(i) for i in sorted(list(n_set))])
        log_message(offspring)
        prid_list = list(set(prid_list) | n_set)

        # add the "legitimate source" ID list to the data dict
        data['prids'] = prid_list
        
        # next, determine "strings to ignore" when comparing texts
        # (1) ignore case name and mandatory section titles (if any)
        to_ignore = [a.case.name]
        for l in EstafetteLeg.objects.filter(template=a.leg.template, number__lte=a.leg.number):
            lt = l.required_section_title
            if lt:
                to_ignore.append(lt)
        # (2) also ignore the assignment case introduction text
        # NOTE: this is HTML, while participants will typically have copied its formatted version,
        #       hence strip the HTML tags and non-breaking spaces
        # NOTE: heuristic to replace introductory text even when it is slightly modified,
        #       is to chunk it by sentence (split text at periods)
        for t in strip_tags(' '.join(a.case.description.split('&nbsp;'))).split('.'):
            st = t.strip()
            # only retain fragments of substantial length (as text is also split at abbreviations!)
            if len(st) > 20:
                to_ignore.append(st)

        # add "strings to ignore" to the data dict
        data['ignore'] = to_ignore
            
        # assume no match with any other file
        max_perc = 0
        min_perc = 0
        # start with empty file scan report
        fsr = []
        # keep track of number of files scanned
        fs_cnt = 0
        # get all relevant assignments to scan (submitted earlier, same case, same leg,
        # same course estafette) and store them (relevant attributes only) in a dictionary
        # NOTE: also scan participant's own earlier work to detect (permitted) auto-plagiarism
        sa_dict = {}
        for sa in Assignment.objects.exclude(time_uploaded__gte=a.time_uploaded
            ).filter(leg__number__lte=a.leg.number, case=a.case,
                     participant__estafette=a.participant.estafette
            ).select_related('participant__student'):
            sa_dict[sa.id] = {'id': sa.id, 'leg': sa.leg.number,
                'author': sa.participant.student.dummy_name(), 'uploaded': sa.time_uploaded}
        # make a list of all IDs of assignments to be scanned
        said_list = sa_dict.keys()

        # add "assignments to scan" ID list to the data dict
        data['saids'] = said_list
        
        # when scanning from scratch, no scanned participant uploads yet
        spuid_list = []

    # reduce sensitivity by ignoring typical text fragments
    to_ignore += COMMON_FRAGMENTS

    # assume that this (resumed) scan will complete the job
    scan_complete = True
    
    # NOTE: for each assignment, multiple files may have been uploaded
    fl = a.leg.file_list()
    for f in fl:
        # only scan DOCX, XLSX and PDF files
        if not ('.docx' in f['types'] or '.xlsx' in f['types'] or '.pdf' in f['types']):
            log_message('Skipping file list item %s(%s)' % (f['name'], f['types']))
            continue
        # find the corresponding upload for the assignment being scanned
        pul = ParticipantUpload.objects.filter(assignment=a, file_name=f['name'])
        if pul:
            file1 = '%s_%s%d' % (f['name'], a.case.letter, a.leg.number)
            pu = pul.first()
            path1 = os.path.join(upl_dir, os.path.basename(pu.upload_file.name))
            text1 = ascii_from_doc(path1, to_ignore)
            # get uploads for all relevant assignments
            u_list = ParticipantUpload.objects.filter(assignment__id__in=said_list,
                file_name=f['name']).exclude(id__in=spuid_list
                ).values('id', 'assignment__id', 'upload_file')
            # scan all uploads, compile the reports in a list, and find highest matching percentage 
            for u in u_list:
                # exit inner loop if maximum scans reached, or maximum time has passed
                # NOTE: we do that here because at this point we know there is still work to do
                if time.time() - start_time > MAX_SECONDS:
                    # indicate that scan is incomplete
                    scan_complete = False
                    break
                sa = sa_dict[u['assignment__id']]
                # workaround to deal with bug (?) in Django that makes that upload_file fields
                # sometimes include the MEDIA_ROOT (without leading slash) and sometimes not
                mr = settings.MEDIA_ROOT.strip(r'\/')
                if u['upload_file'].find(mr) == 0:
                    path2 = settings.LEADING_SLASH + u['upload_file']
                else:
                    path2 = os.path.join(settings.MEDIA_ROOT, u['upload_file'])
                file2 = '%s_%s%d' % (f['name'], a.case.letter, sa['leg'])
                # NOTE: the author's participant ID will allow identification by dummy_name(),
                #       the upload time is relevant info for the report, and the scanner should know
                #       whether the assignment is some predecessor, or offspring thereof
                p, r = scan_report(text1, file2, path2, u['assignment__id'], sa['author'],
                    sa['uploaded'].strftime('%Y-%m-%d %H:%M'),
                    u['assignment__id'] in prid_list, MATCH_THRESHOLD, to_ignore)
                fsr.append(r)
                # keep track of high AND low values (the latter indicating a match with RELATED work)
                max_perc = max(p, max_perc)
                min_perc = min(p, min_perc)
                fs_cnt += 1
                # add upload ID to list of scanned upload IDs
                spuid_list.append(u['id'])
        # when maximum duration reached, also exit outer loop
        if time.time() - start_time > MAX_SECONDS:
            break

    # TO DO: also scan assignment items
    # NOTE: all assignment items are collated into to a single string, which is then
    #       stripped from all its HTML tags (as item texts are HTML)
    # NOTE: this stripping is done "smartly" so that, e.g., </li><li> and </p><p> are
    #       replaced by a space to avoid sticking words together    

    if scan_complete:
        # report the results
        t_diff = time.time() - start_time
        log_message('%d%% match; %d%% with related work (%d files scanned; %4.3f seconds)'
            % (max_perc, abs(min_perc), fs_cnt, t_diff))
        fsr.append('_SCAN COMPLETED: %d files scanned. Scan took %4.3f seconds._'
            % (fs_cnt, t_diff))
        # write result to file in Markdown format
        content = ('##%d%% \n_Scanned on %s_\n\n' % (max_perc,
            timezone.now().strftime('%Y-%m-%d %H:%M'))) + '\n\n'.join(fsr)
        with open(report_path, 'wb') as text_file:
            text_file.write(content.encode('utf-8'))
        # update time scanned attribute of assignment
        a.time_scanned = timezone.now()
        # print "MIN = %d; MAX = %d" % (min_perc, max_perc)
        # NOTE: if 5% or more overlap, or more unrelated overlap than related overlap,
        #       show this percentage
        if max_perc >= 5 or max_perc > abs(min_perc):
            a.scan_result = max_perc
        else:
            a.scan_result = min_perc
        a.save()
        # remove the progress file
        try:
            os.remove(progress_path)
        except:
            pass
        # style the first header to make it display in the appropriate status color 
        content = markdown(content).replace('<h2>',
            '<h2 style="color: %s">' % status_color(max_perc), 1)
        # return tuple with max report in HTML format
        return (max_perc, content)
    else:
        # report the incomplete scan
        t_diff = time.time() - start_time
        log_message('INCOMPLETE scan -- %d%% match; %d%% with related work (%d files scanned; %4.3f seconds)'
            % (max_perc, abs(min_perc), fs_cnt, t_diff))
        fsr.append('_Scan still partial -- %d files scanned. Scan took %4.3f seconds._'
            % (fs_cnt, t_diff))
        # add the report to the data dict
        data['author'] = author
        data['min_perc'] = min_perc
        data['max_perc'] = max_perc
        data['fsr'] = fsr
        data['fs_cnt'] = fs_cnt
        # add the list of scanned upload files
        data['spuids'] = spuid_list
        # unset the "busy" flag
        if 'busy' in data:
            del data['busy']
        # overwrite the provisionary progress file
        with open(progress_path, 'w') as f:
            f.write(dumps(data))
        return (max_perc, '<p><em>Scan still incomplete (%d checked)</em></p>' % fs_cnt)

# looks for some yet unscanned assignment and scans it
# NOTE: as scanning may take several seconds, this function is not called when a student
#       uploads (as this may itself take time, and the user may become anxious);
#       instead, it is called when user performs any action except 'upload'
def scan_one_assignment():
# NOTE: the two lines below show how to clear scan results for a specific repaly
#    Assignment.objects.filter(participant__estafette__id=27, leg__number=1).update(
#        time_scanned=DEFAULT_DATE, scan_result=0)
    try:
        a = Assignment.objects.exclude(time_uploaded__lte=DEFAULT_DATE
            ).filter(time_scanned__lte=DEFAULT_DATE, clone_of=None,
                participant__student__dummy_index=0
            ).values_list('id', flat=True)[:1]
        if a:
            scan_assignment(a[0])
    except Exception, e:
        # catch errors to log them (should not be visible to participant)
        log_message('ERROR during single scan: %s' % str(e))


# scans up to N assignments
# NOTE: this function may take very long to execute should NOT be called from a script!
def scan_N_assignments(n):
    a = Assignment.objects.exclude(time_uploaded__lte=DEFAULT_DATE
        ).filter(time_scanned__lte=DEFAULT_DATE, clone_of=None
        ).values_list('id', flat=True)
    print "%d assignments still need scanning" % a.count()
    if a:
        n = min(n, a.count())
    else:
        print "No scan needed"
        return
    i = 0
    while i < n:
        i += 1;
        print "Scanning #%d of %d" % (i, n)
        try:
            scan_assignment(a[i-1])
        except Exception, e:
            # catch errors to log them (should not be visible to participant)
            log_message('ERROR during single scan: %s' % str(e))

