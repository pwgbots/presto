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

from .models import EstafetteLeg


# returns string with key words (double quoted) that are required for assignment a,
# but appear to be missing in Word document doc
def missing_key_words(a, doc):
    # key word list compiles case keywords and keywords for this and all preceding steps 
    kwl = a.case.required_keywords.split(';')
    for l in EstafetteLeg.objects.filter(template=a.leg.template).exclude(number__gt=a.leg.number):
        kwl += l.required_keywords.split(';')
    missing_kw = []
    for kw in kwl:
        # ignore leading and trailing whitespace, and convert all inner whitespace to a single space
        w = ' '.join(kw.strip().split())
        # if key word contains one or more upper case characters, this is interpreted as mandatory
        ignore_case = w == w.lower()
        if ignore_case:
            ucw = w.upper()
        # assume that the word is NOT mentioned
        m = False
        for par in doc.paragraphs:
            # reduce all white space to a single one, including "non-breaking spaces"
            txt = ' '.join(par.text.replace(unichr(160), ' ').strip().split())
            if ignore_case:
                m = ucw in txt.upper()
            else:
                m = w in txt
            if m:
                break
        if not m:
            for tbl in doc.tables:
                for row in tbl.rows:
                    for cell in row.cells:
                        for par in cell.paragraphs:
                            # reduce all white space to a single one, including "non-breaking spaces"
                            txt = ' '.join(par.text.replace(unichr(160), ' ').strip().split())
                            if ignore_case:
                                m = ucw in txt.upper()
                            else:
                                m = w in txt
                            if m:
                                break
                        if m:
                            break
                    if m:
                        break
                if m:
                    break
        # if not mentioned in any paragraph, add it to the missing word list
        if not m:
            missing_kw.append(w)
    # return missing key words as string, or None if empty list
    if missing_kw:
        return '"' + '", "'.join([w for w in missing_kw]) + '"'
    return None

# returns word count of text following section name s, or False if the section
# appears to be missing in Word document doc
# NOTE: Stripping ALL whitespace is needed because students typically insert spaces into
#       longer words, and this can be tolerated without major consequences
def has_section(doc, s):
    # count number of words in section title (after replacing non-breaking spaces by normal ones)
    s = s.replace(unichr(160), ' ').split()
    # to prevent false positives, we ignore paragraphs longer than the section length plus 5 words
    # so that prexifxes like "Section number 1." are accepted, but title phrase embedded in longer
    # paragraphs ignored.
    max_cnt = len(s) + 5
    # strip ALL whitespace from section title and convert it to upper case
    s = ''.join(s).upper()
    word_cnt = 0
    searching = True
    for par in doc.paragraphs:
        w_list = par.text.replace(unichr(160), ' ').split()
        w_cnt = len(w_list)
        # print ''.join(w_list).upper().encode('utf-8')
        if w_cnt <= max_cnt and searching:
            searching = not (s in ''.join(w_list).upper())
        # test again, because word count should include title words
        if not searching:
            word_cnt += w_cnt
    # return section word count, or None if section title not found
    if searching:
        return None
    return word_cnt

# returns string with sections (double quoted) that are required for assignment a,
# but appear to be missing (or too short) in Word document doc
def missing_sections(a, doc):
    # initialize word count of next section (hence initially 0) and missing string  
    next_swc = 0
    missing = []
    lang = a.participant.student.course.language
    # get list of section titles in reverse order of steps
    for l in EstafetteLeg.objects.filter(template=a.leg.template
        ).exclude(number__gt=a.leg.number).order_by('-number'):
        title = l.required_section_title
        min_length = l.required_section_length
        if title:
            swc = has_section(doc, title)
            if swc is None:
                missing.insert(0, lang.phrase('Section_missing') % (l.number, title))
            else:
                if swc - next_swc < min_length:
                    missing.insert(0, lang.phrase('Section_too_short') %
                        (l.number, title, swc - next_swc, min_length))
                next_swc = swc
                # print "SWC = %d" % next_swc
    # return missing section titles as string, or None if empty list
    if missing:
        return '<br/>'.join([ttl for ttl in missing])
    return None
