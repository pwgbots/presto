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

from .models import EstafetteLeg

from zipfile import ZipFile


def contains_comments(path):
    """Return True if the designated document contains comments."""
    try:
        # test whether the file is a docx, pptx or xlsx (i.e., a ZIP file)
        with ZipFile(path, 'r') as zf:
            # it is a ZIP file; now see if it contains "suspect" files
            suspects = [
                'comments/', 'word/comm', 'word/peop', 'ppt/comme', 'xl/commen'
                ]
            for i in zf.infolist():
                if i.filename[:9] in suspects:
                    return True
    except Exception as e:
        pass
    return False    


def missing_key_words(a, doc):
    """
    Return string with key words (double quoted) that are missing.
    
    Required key words may have been specified for assignment a, both for its
    case and for its step, so check whether some such words but appear to be
    missing in Word document doc.
    """
    # key word list kwl compiles case keywords and keywords for this AND all
    # preceding steps 
    kwl = a.case.required_keywords.split(';')
    for l in EstafetteLeg.objects.filter(
            template=a.leg.template).exclude(number__gt=a.leg.number):
        kwl += l.required_keywords.split(';')
    missing_kw = []
    for kw in kwl:
        # Ignore leading and trailing whitespace, and convert all inner
        # whitespace to a single space.
        w = ' '.join(kw.strip().split())
        # If key word contains one or more upper case characters, this is
        # interpreted as mandatory.
        ignore_case = w == w.lower()
        if ignore_case:
            ucw = w.upper()
        # Assume that the word is NOT mentioned.
        m = False
        if type(doc).__name__ == 'Document':
            for par in doc.paragraphs:
                # reduce all white space to a single one, including "non-breaking spaces"
                txt = ' '.join(par.text.replace('\u00A0', ' ').strip().split())
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
                                txt = ' '.join(par.text.replace('\u00A0', ' ').strip().split())
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
        # Otherwise, doc is a string.
        elif ignore_case:
            m = ucw in ' '.join(doc.strip().split()).upper()
        else:
            m = w in ' '.join(doc.strip().split())
        # If word is not mentioned, add it to the missing word list.
        if not m:
            missing_kw.append(w)
    # return missing key words as string, or None if empty list
    if missing_kw:
        return '"' + '", "'.join([w for w in missing_kw]) + '"'
    return None


def has_section(doc, s):
    """
    Return False if section s is missing in doc, or too short.

    NOTES:
    (1) Assumes that section s is the LAST section of the document, and hence
        counts ALL words in the doc that follow section title s.
    (2) Stripping ALL whitespace is needed because students typically insert
        spaces into longer words, and this can be tolerated without major
        consequences.
    (3) Short section titles can also occur somewhere in the midst of the
        document text. To prevent false positives, we ignore paragraphs
        longer than the section length plus 4 words, so that prefixes like
        "Section number 1." are accepted, but title phrase embedded in longer
        paragraphs ignored.
    """
    # replace non-breaking spaces by normal ones
    s = s.replace('\u00A0', ' ').split()
    # set the max. word count to consider it still as a section title
    max_cnt = len(s) + 4
    # strip ALL whitespace from section title and convert it to upper case
    s = ''.join(s).upper()
    word_cnt = 0
    # use searching to indicate whether the title has been found 
    searching = True
    for par in doc.paragraphs:
        w_list = par.text.replace('\u00A0', ' ').split()
        w_cnt = len(w_list)
        if w_cnt <= max_cnt and searching:
            searching = not (s in ''.join(w_list).upper())
        # test again, because word count should include title words
        if not searching:
            word_cnt += w_cnt
    # return section word count, or None if section title not found
    if searching:
        return None
    return word_cnt


def missing_sections(a, doc):
    """
    Return a string with sections that are required for a but missing in doc.

    Assignment a can specify required section titles as well as their minimum
    word count, so check whether such sections appear to be missing or too short
    in the Word document doc.
    """
    # initialize word count of next section (hence initially 0) and missing string  
    next_swc = 0
    missing = []
    lang = a.participant.student.course.language
    # get list of section titles in reverse order of steps
    for l in EstafetteLeg.objects.filter(
        template=a.leg.template
        ).exclude(number__gt=a.leg.number).order_by('-number'):
        
        title = l.required_section_title
        min_length = l.required_section_length
        if title:
            swc = has_section(doc, title)
            if swc is None:
                missing.insert(
                    0,
                    lang.phrase('Section_missing').format(
                        nr=l.number,
                        ttl=title
                        )
                    )
            else:
                if swc - next_swc < min_length:
                    missing.insert(
                        0,
                        lang.phrase('Section_too_short').format(
                            nr=l.number,
                            ttl=title,
                            cnt=swc - next_swc,
                            min=min_length
                            )
                        )
                next_swc = swc

    # return missing section titles as string, or None if empty list
    if missing:
        return '<br>'.join([ttl for ttl in missing])
    return None
