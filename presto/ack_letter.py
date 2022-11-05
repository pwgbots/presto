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
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from wsgiref.util import FileWrapper

from .models import LetterOfAcknowledgement

# python modules
from fpdf import FPDF, set_global
from html.parser import HTMLParser
import os
import sys
from tempfile import mkstemp
import traceback

# presto modules
from presto.generic import generic_context, has_role, inform_user, report_error, warn_user
from presto.utils import decode, encode, log_message, plural_s, random_hex

VERIFICATION_URL = 'https://presto.tudelft.nl/verify'

DELFTX_LOGO = os.path.join(settings.IMAGE_DIR, 'delftx.png')
EDX_LOGO = os.path.join(settings.IMAGE_DIR, 'edx.png')

DEJAVU_FONT = os.path.join(settings.FONT_DIR, 'DejaVuSansCondensed.ttf')
DEJAVU_OBLIQUE_FONT = os.path.join(settings.FONT_DIR, 'DejaVuSansCondensed-Oblique.ttf')
DEJAVU_BOLD_FONT = os.path.join(settings.FONT_DIR, 'DejaVuSansCondensed-Bold.ttf')
DEJAVU_BOLD_OBLIQUE_FONT = os.path.join(settings.FONT_DIR, 'DejaVuSansCondensed-BoldOblique.ttf')

POINT_TO_MM = 0.3528

# NOTE: This setting is needed to prevent error during AddFont.
set_global('FPDF_CACHE_MODE', 1)


class HTMLtoPDFParser(HTMLParser):
    pdf = None
    margin = 25
    pos_x = 0
    pos_y = 0
    indent = 0
    spacing = 3
    text_width = 160
    font_family = 'DejaVu'
    font_size = 10
    justify = True
    relative_size = 1
    v_offset = 0
    bold = False
    italic = False
    underline = False
    code = False
    item = False
    bullets = [u'\u2022', u'\u25E6', u'\u25B8', u'\u25B9', u'\u25AA', u'\u25AB']
    item_number = []
    header_level = 0
    line_width = 0
    word_list = []
    
    def set_pdf(self, pdf):
        self.pdf = pdf
    
    def font(self):
        style = ''
        if self.bold:
            style += 'B'
        if self.italic:
            style += 'I'
        if self.underline:
            style += 'U'
        size = self.font_size * self.relative_size
        if self.header_level:
            size += (1 - 0.15*self.header_level) * size
        if self.code:
            family = 'Courier'
        else:
            family = 'DejaVu'
        return {'family': family, 'style': style, 'size': size}
    
    def handle_starttag(self, tag, attrs):
        if tag == 'strong':
            self.bold = True
        elif tag == 'em':
            self.italic = True
        elif tag == 'u':
            self.underline = True
        elif tag == 'code':
            self.code = True
        elif tag == 'sub':
            self.relative_size *= 0.7
            self.v_offset += self.relative_size * 0.5
        elif tag == 'sup':
            self.relative_size *= 0.7
            self.v_offset -= self.relative_size * 0.5
        elif tag == 'small':
            self.relative_size *= 0.8
        elif tag == 'large':
            self.relative_size *= 1.25
        elif tag[0] == 'h':
            self.header_level = int(tag[1])
        elif tag == 'p':
            self.new_line()
            self.pdf.set_x(self.indent)
        elif tag == 'ol':
            self.new_line()
            self.item_number.append(1)  # 1 indicates: next item has number 1
        elif tag == 'ul':
            self.new_line()
            self.item_number.append(0)  # 0 indicates: no item numbering
        elif tag == 'li':
            i = len(self.item_number) - 1
            if self.item_number[i] == 0:
                self.indent += 4
            else:
                self.indent += 6
            self.item = True

    def handle_endtag(self, tag):
        if tag == 'strong':
            self.bold = False
        elif tag == 'em':
            self.italic = False
        elif tag == 'u':
            self.underline = False
        elif tag == 'code':
            self.code = False
        elif tag == 'sub':
            self.v_offset -= self.relative_size * 0.5
            self.relative_size *= 0.7
        elif tag == 'sup':
            self.v_offset += self.relative_size * 0.5
            self.relative_size *= 0.7
        elif tag == 'small':
            self.relative_size *= 1.25
        elif tag == 'large':
            self.relative_size *= 0.8
        elif tag[0] == 'h':
            self.new_line()
            self.header_level = 0
        elif tag == 'p':
            self.new_line()
        elif tag == 'ol' or tag == 'ul':
            self.item_number.pop()
        elif tag == 'li':
            if self.word_list:
                self.new_line()
            i = len(self.item_number) - 1
            if self.item_number[i] == 0:
                self.indent -= 4
            else:
                self.item_number[i] += 1
                self.indent -= 6

    def new_line(self, justify = False):
        # print("new line ({} words)".format(len(self.word_list)))
        top_offset = 0
        bottom_offset = 0
        height = self.font_size * POINT_TO_MM * 0.6
        base_line = height
        if self.word_list:
            height = 0
            for w in self.word_list:
                top_offset = max(top_offset, -w['offset'])
                bottom_offset = max(bottom_offset, w['offset'])
                height = max(height, w['font']['size'] * POINT_TO_MM * 0.6)
            baseline = self.margin + self.pos_y + top_offset + height
            if self.item:
                self.pos_x = self.indent
                i = len(self.item_number) - 1
                if self.item_number[i] == 0:
                    self.pdf.set_xy(self.margin + self.pos_x - 4, baseline - height)
                    self.pdf.cell(2, height, self.bullets[i])
                else:
                    self.pdf.set_xy(self.margin + self.pos_x - 6, baseline - height)
                    self.pdf.cell(4, height, '{}.'.format(self.item_number[i]))
                self.item = False
            if justify and len(self.word_list) > 1:
                xs = (self.text_width - self.line_width - self.indent) * (1.0 / len(self.word_list))
            else:
                xs = 0
            for w in self.word_list:
                print(w)
                f = w['font']
                h = f['size'] * POINT_TO_MM * 0.6
                self.pdf.set_xy(self.margin + self.pos_x, baseline - h + w['offset'])
                self.pdf.set_font(f['family'], f['style'], f['size'])
                sw = self.pdf.get_string_width(' ')
                self.pdf.cell(w['width'] + sw + xs, h, w['text'])
                self.pos_x += w['width'] + sw + xs
            self.word_list = []
        
        # move one line down and to the left
        self.pos_x = self.indent
        self.pos_y += base_line + self.spacing * POINT_TO_MM * height
        self.line_width = 0

    def word(self, w):
        # set font so that get_string_width will return correct value
        f = self.font()
        self.pdf.set_font(f['family'], f['style'], f['size'])
        ww = self.pdf.get_string_width(w)
        # print('w="{}", width={:%3.1f}, pos_x={:3.1f}'.format(w, ww, self.line_width))
        if self.indent + self.line_width + ww >= self.text_width:
            self.new_line(self.justify)
        self.word_list.append({
            'text': w,
            'font': f,
            'width': ww,
            'offset': self.v_offset
            })
        # also add width of a space
        self.line_width += ww + self.pdf.get_string_width(' ')

    def handle_data(self, data):
        for w in data.split():
            self.word(w)


class MyFPDF(FPDF):

    # puts header
    def letter_head(self, code, date, subject):
        # small font for captions and info text
        self.set_font('DejaVu', '', 8)
        self.set_xy(25, 10)
        self.cell(30, 5, 'Authentication:')
        self.set_xy(25, 20)
        self.cell(30, 5, 'First issued:')
        self.set_xy(25, 27)
        self.cell(30, 5, 'Subject:')
        self.set_font('DejaVu', 'I', 8)
        self.set_xy(46, 14)
        self.cell(
            80,
            5,
            '(follow this link, or verify the code on {url})'.format(
                url=VERIFICATION_URL
                ),
            ln=1,
            align='L'
            )
        # larger font for actual entries
        self.set_font('DejaVu', style='U', size=10)
        self.set_xy(46, 10)
        self.set_text_color(0, 173, 238)
        self.cell(80, 5, code, link=(VERIFICATION_URL + '/' + code))
        self.set_font('DejaVu', size=10)
        self.set_text_color(0, 0, 0)
        self.set_xy(46, 20)
        self.cell(80, 5, date)
        self.set_xy(46, 27)
        self.cell(80, 5, subject)
        # show DelftX logo on the right 
        self.image(DELFTX_LOGO, x=145, y=10, w=55)
        self.cell(w=55)
        
    # puts 'Page P (of N)' at bottom of page
    def footer(self):
        self.set_y(-15)
        self.set_font('DejaVu', size=8)
        self.cell(0, 10, 'Page {n} (of 2)'.format(n=self.page_no()), align='C')

    # adds letter text with referee-related fields from database
    def main_text(self, text):
        self.set_font('DejaVu', size=10)
        self.set_xy(25, 50)
        self.multi_cell(160, 6, text)

    # adds footnote with disclaimer (mentioning edX in color)
    def footnote(self, mail):
        self.set_font('DejaVu', size=9)
        self.set_xy(25, -35)
        self.cell(0, 5, '* E-mail address:  ' + mail)
        self.set_xy(27, -31)
        self.cell(0, 5, 'The ID of the participant is verified by      . '
                + 'The assessment is not proctored in a formal exam setting.'
            )
        # position the edX logo on the blanks following "verified by"
        self.image(EDX_LOGO, x=82.9, y=267.15, w=5)
        self.cell(w=5)

    def page_2(self, rd):
        self.add_page()
        print(rd)
        # prepare the HTML to be rendered on this page
        html = ('<h3>Description of course <em>%s</em> (%s)</h3><p>(started %s; ended %s)</p>%s' %
            (rd['CN'], rd['CC'], rd['CSD'], rd['CED'], rd['CD']))
        print(html)
        # instantiate the parser and feed it the HTML
        parser = HTMLtoPDFParser()
        parser.set_pdf(self)
        parser.feed(html)
        parser.new_line()

    # set PDF document properties
    def set_properties(self, code, task, name, nr, timestamp):
        self.set_author('DelftX - Authenticity of this letter can be verified at ' + VERIFICATION_URL)
        self.set_creator('presto.tudelft.nl')
        self.set_keywords('Authentication code: ' + code)
        self.set_title('Acknowledgement of ' + task)
        self.set_subject(
            'Letter issued to {n}. Copy #{c} rendered on {t}.'.format(
                n=name,
                c=nr,
                t=timestamp
                )
            )


@login_required(login_url=settings.LOGIN_URL)
def ack_letter(request, **kwargs):
    # NOTE: Downloading a file opens a NEW browser tab/window, meaning that
    #       the coding keys should NOT be rotated; this is achieved by passing
    #       "NOT" as test code.
    context = generic_context(request, 'NOT')
    # Check whether user can have student role.
    if not has_role(context, 'Student'):
        return render(request, 'presto/forbidden.html', context)
    try:
        h = kwargs.get('hex', '')
        # Verify that letter exists.
        # NOTE: Since keys have not been rotated, use the ENcoder here!
        lid = decode(h, context['user_session'].encoder)
        # get letter properties
        loa = LetterOfAcknowledgement.objects.get(id=lid)
        # Update fields, but do not save yet because errors may still prevent
        # effective rendering.
        loa.time_last_rendered = timezone.now()
        loa.rendering_count += 1
        # Get the dict with relevant LoA properties in user-readable form.
        rd = loa.as_dict()
        # Create letter as PDF.
        pdf = MyFPDF()
        pdf.add_font('DejaVu', '', DEJAVU_FONT, uni=True)
        pdf.add_font('DejaVu', 'I', DEJAVU_OBLIQUE_FONT, uni=True)
        pdf.add_font('DejaVu', 'B', DEJAVU_BOLD_FONT, uni=True)
        pdf.add_font('DejaVu', 'BI', DEJAVU_BOLD_OBLIQUE_FONT, uni=True)
        pdf.add_page()
        # see whether course has a description; if so, make a reference to page 2 and
        # and prepare the text for this page 2
        if rd['CD']:
            see_page_2 = ' described on page 2'
        else:
            see_page_2 = ''
        # NOTE: if the RID entry (= the referee ID) equals zero, the letter is a participant LoA!
        if rd['RID'] == 0:
            pdf.letter_head(rd['AC'], rd['DI'], 'Acknowledgement of Project Relay completion')
            # add the participant acknowledgement text to the letter
            text = ''.join(['To whom it may concern,\n\n',
                'With this letter, DelftX, an on-line learning initiative of Delft University of',
                ' Technology through edX, congratulates ', rd['FN'], '* for having completed',
                ' the project relay ', rd['PR'],' offered as part of the online course ',
                rd['CN'], see_page_2, '.\n\n',
                'A project relay comprises a series of steps: assignments that follow on from',
                ' each other. In each step, participants must first peer review, appraise, and',
                ' then build on the preceding step submitted by another participant.\n\n',
                'The project relay ', rd['PR'],' comprised ', rd['SL'],
                ', where each step posed an intellectual challenge that will have required',
                ' several hours of work. DelftX appreciates in particular the contribution that',
                ' participants make to the learning of other participants by giving feedback',
                ' on their work.\n\n\n',
                rd['SN'], '\n', rd['SP']])
        else:
            pdf.letter_head(rd['AC'], rd['DI'], 'Project Relay Referee Letter of Acknowledgement')
            # adapt some text fragments to attribute values
            cases = plural_s(rd['ACC'], 'appeal case')
            hours = plural_s(rd['XH'], 'hour')
            # average appreciation is scaled between -1 and 1
            if rd['AA'] > 0: 
                appr = ' The participants involved in the appeal were appreciative of the arbitration.'
            elif rd['AA'] < -0.5: 
                appr = ' Regrettably, the participants involved in the appeal were generally not appreciative of the arbitration.'
            else:
                appr = ''
            if rd['DFC'] == rd['DLC']:
                period = 'On ' + rd['DLC']
            else:
                period = 'In the period between {} and {}'.format(rd['DFC'], rd['DLC'])
            # add the referee acknowledgement text to the letter
            text = ''.join(['To whom it may concern,\n\n',
                'With this letter, DelftX, an on-line learning initiative of Delft University of Technology',
                ' through edX, wishes to express its gratitude for the additional efforts made by ', rd['FN'],
                '* while participating in the project relay ', rd['PR'],
                ' offered as part of the online course ', rd['CN'], see_page_2, '.\n\n',
                'A project relay comprises a series of steps: assignments that follow on from each other. ',
                'In each step, participants must first peer review, appraise, and then build on the ',
                'preceding step submitted by another participant. Participant ', rd['FN'],
                ' has not only completed the course, but also passed the referee test for ', rd['SL'],
                ' of the ', rd['PR'], ' project relay. This implies having a better command of the subject',
                ' taught than regular participants.\n\n',
                'Referees arbitrate appeal cases, i.e., situations where the reviewed participant ',
                'disagrees with the reviewer\'s critique and/or appraisal. ', period, ', participant ',
                rd['FN'], ' has arbitrated on ', cases, '. This corresponds to approximately ', hours,
                ' of work.', appr, '\n\nThe role of referee is indispensable to run project ',
                'relays on a large scale. DelftX therefore greatly values participants volunteering to ',
                'act as such, since it requires significant effort on top of the regular assignments.\n\n\n',
                rd['SN'], '\n', rd['SP']])
        pdf.main_text(text)
        # add footnote with disclaimer
        pdf.footnote(rd['EM'])
        if see_page_2:
            pdf.page_2(rd)
        # set document properties
        if rd['RID'] == 0:
            task = 'completing a project relay'
        else:
            task = 'work as project relay referee'
        pdf.set_properties(rd['AC'], task, rd['FN'], rd['RC'], rd['TLR'])
        # output to temporary file
        temp_file = mkstemp()[1]
        pdf.output(temp_file, 'F')
        log_message('Rendering acknowledgement letter for ' + rd['PR'], context['user'])
        # push the PDF as attachment to the browser
        w = FileWrapper(file(temp_file, 'rb'))
        response = HttpResponse(w, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="presto-LoA.pdf"'
        # now we can assume that the PDF will appear, so the updated letter data can be saved
        loa.save()
        return response
    except Exception as e:
        report_error(context, e)
        return render(request, 'presto/error.html', context)
