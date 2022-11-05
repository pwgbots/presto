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
from django.core.files.base import ContentFile
from django.db.models import Count
from django.http import HttpResponse
from django.utils import timezone

from .models import CourseEstafette, Participant, Assignment, PeerReview, DEFAULT_DATE

# python modules
from datetime import datetime
from io import BytesIO
import math
import os
from PIL import Image, ImageDraw, ImageFont

# presto modules
from presto.generic import generic_context, has_role, change_role
from presto.teams import team_assignments, team_final_reviews, team_lookup_dict
from presto.utils import encode, decode, log_message

IMG_WIDTH = 540   # not too wide as it should download rapidly
IMG_HEIGHT = 320  # with 100% complete = bar of 250px high, this leaves enough space for legend
BAR_CNT = 120     # number of time steps = vertical bars in chart
BAR_WIDTH = 4     # width of a single bar; 120 bars = 480px chart area width
V_AXIS_X = 55     # this leaves 50px for percentages text on the left, and 5px margin on the right
H_AXIS_Y = 265    # this leaves 55px margin for legend

DAY_TIME = '%d-%m %H:%M'

# view for progress "page"
# NOTE: this view does not render a page, but sends a PNG file to the browser
@login_required(login_url=settings.LOGIN_URL)
def progress(request, **kwargs):
    # NOTE: a downloaded image is part the current page, meaning that the coding keys
    # should NOT be rotated; this is achieved by passing "NOT" as test code.
    context = generic_context(request, 'NOT')
    if True:
        # check whether user can have student role
        if not (has_role(context, 'Student') or has_role(context, 'Instructor')):
            raise Exception('No access')
        h = kwargs.get('hex', '')
        # verify that hex code is valid
        # NOTE: since keys have not been rotated, use the ENcoder here!
        oid = decode(h, context['user_session'].encoder)
        # check whether oid indeed refers to an existing participant or course estafette
        p_or_ce = kwargs.get('p_or_ce', '')
        if p_or_ce == 'p':
            p = Participant.objects.get(pk=oid)
            ce = p.estafette
        else:
            p = None
            ce = CourseEstafette.objects.get(pk=oid)
            
        # get the basic bar chart
        img = update_progress_chart(ce)

        # if image requested by a participant, add orange markers for his/her uploads
        if p:
            draw = ImageDraw.Draw(img)
            # get a font (merely to draw nicely anti-aliased circular outlines)
            fnt = ImageFont.truetype(os.path.join(settings.FONT_DIR, 'segoeui.ttf'), 25)
            # calculate how many seconds of estafette time is represented by one bar
            time_step = int((ce.end_time - ce.start_time).total_seconds() / BAR_CNT) + 1
            # get the number of registered participants (basis for 100%)
            p_count = Participant.objects.filter(estafette=ce).count()
            # get leg number and upload time of all uploaded assignments for this participant
            a_list = team_assignments(p).values('leg__number', 'time_uploaded')
            for a in a_list:
                # get the number of assignments submitted earlier
                cnt = Assignment.objects.filter(participant__estafette=ce
                    ).filter(leg__number=a['leg__number']
                    ).filter(time_uploaded__gt=DEFAULT_DATE
                    ).filter(clone_of__isnull=True
                    ).exclude(time_uploaded__gt=a['time_uploaded']
                    ).count()
                bar = int((a['time_uploaded'] - ce.start_time).total_seconds() / time_step)
                perc = round(250 * cnt / p_count)
                x = V_AXIS_X + bar * BAR_WIDTH
                y = H_AXIS_Y - perc - 5
                # mark uploads with orange & white outline (10 pixels diameter)
                draw.ellipse([x, y, x + 10, y + 10],
                    fill=(236, 127, 44, 255), outline=None)
                # draw white letter o to produce neat circular outline
                draw.text((x-1.5, y-14.5), 'o', font=fnt, fill=(255, 255, 255, 255))
            # get nr and submission time for this participant's final reviews
            nr_of_steps = ce.estafette.template.nr_of_legs()
            r_set = team_final_reviews(p).values('reviewer__id', 'time_submitted'
                ).order_by('reviewer__id', 'time_submitted')
            r_index = 0
            for r in r_set:
                r_index += 1
                # get the number of final reviews submitted earlier
                cnt = PeerReview.objects.filter(reviewer__estafette=ce
                    ).filter(assignment__leg__number=nr_of_steps
                    ).filter(time_submitted__gt=DEFAULT_DATE
                    ).exclude(time_submitted__gt=r['time_submitted']
                    ).values('reviewer__id', 'time_submitted'
                    ).order_by('reviewer__id', 'time_submitted'
                    ).annotate(rev_cnt=Count('reviewer_id')
                    ).filter(rev_cnt=r_index).count()
                bar = int((r['time_submitted'] - ce.start_time).total_seconds() / time_step)
                perc = round(250 * cnt / p_count)
                x = V_AXIS_X + bar * BAR_WIDTH
                y = H_AXIS_Y - perc - 5
                # mark final reviews with orange
                draw.ellipse([x, y, x + 10, y + 10],
                    fill=(236, 127, 44, 255), outline=None)
                # draw black letter o to produce neat circular outline
                draw.text((x-1.5, y-14.5), 'o', font=fnt, fill=(0, 0, 0, 255))
        # output image to browser (do NOT save it as a file)
        response = HttpResponse(content_type='image/png')
        img.save(response, 'PNG')
        return response
    try:
        print('HERE')
    except Exception as e:
        log_message(
            'ERROR while generating progress chart: ' + str(e),
            context['user']
            )
        with open(os.path.join(settings.IMAGE_DIR, 'not-found.png'), "rb") as f:
            return HttpResponse(f.read(), content_type="image/png")


# returns the progress bar chart image for course estafette ce 
def update_progress_chart(ce):
    # calculate how many seconds of estafette time is represented by one bar
    time_step = int((ce.end_time - ce.start_time).total_seconds() / BAR_CNT) + 1
    # one count array for every estafette leg...
    nr_of_steps = ce.estafette.template.nr_of_legs()
    # initialize arrays with y-values to zero
    y = [[0.0 for col in range(BAR_CNT + 1)]
        for row in range(nr_of_steps + ce.final_reviews + 1)]
    # get the bin number corresponding to the present time
    t_start = ce.start_time
    t_now = timezone.now()
    present_bin = min(int((t_now - t_start).total_seconds() / time_step), BAR_CNT)
    # get the number of registered participants (basis for 100%)
    # NOTE: do not count "instructor participants" (having dummy index < 0)
    p_count = Participant.objects.filter(estafette=ce).exclude(student__dummy_index__lt=0).count()
    # get registration time for all participants in this course estafette
    prog_set = Participant.objects.filter(estafette=ce).exclude(student__dummy_index__lt=0
        ).filter(time_started__gt=DEFAULT_DATE).values('time_started')
    # each participant should add 1 to the bin for their starting time
    leg_index = nr_of_steps # highest index in y-array
    for p in prog_set:
        bin_nr = max(int((p['time_started'] - t_start).total_seconds() / time_step), 0)
        # protect against "ghost participants" that started after the end time
        if bin_nr <= BAR_CNT:
            y[leg_index][bin_nr] += 1.0
    # get the dict with team composition
    team_dict = team_lookup_dict(ce)
    # get leg number and upload time for all *uploaded* assignments for this course estafette
    prog_set = Assignment.objects.filter(participant__estafette=ce
        ).filter(time_uploaded__gt=DEFAULT_DATE
        ).filter(clone_of__isnull=True
        ).values('participant__id', 'leg__number', 'time_uploaded')
    # each assignment should add 1 to the bin for its uploading time
    for a in prog_set:
        leg_index = nr_of_steps - a['leg__number']  # leg numbers start at 1, so 0 = last leg
        bin_nr = max(int((a['time_uploaded'] - t_start).total_seconds() / time_step), 0)
        # protect against late uploads (after the end time) -- just in case
        if bin_nr <= BAR_CNT:
            pcnt = 1.0
            # see if assignment has been submitted by a team leader
            t_entry = team_dict.get(a['participant__id'], None)
            if t_entry:
                if type(t_entry) is list:
                    # if so, add number of members still on the team at the time of submission
                    for tpl in t_entry:
                        if a['time_uploaded'] < tpl[1]:
                            pcnt += 1.0
            y[leg_index][bin_nr] += pcnt
    # get final reviews for this estafette
    prog_set = PeerReview.objects.filter(reviewer__estafette=ce
        ).filter(assignment__leg__number=nr_of_steps
        ).filter(time_submitted__gt=DEFAULT_DATE
        ).exclude(reviewer__student__dummy_index__lt=0
        ).values('reviewer__id', 'final_review_index', 'time_submitted'
        ).order_by('reviewer__id', 'time_submitted')
    # each review should add 1 to the bin for its submission time
    for r in prog_set:
        rev_index = nr_of_steps + r['final_review_index']
        bin_nr = max(int((r['time_submitted'] - t_start).total_seconds() / time_step), 0)
        # protect against late reviews (e.g., instructor reviews submitted after closure)
        if bin_nr <= BAR_CNT:
            pcnt = 1.0
            # see if assignment has been submitted by a team leader
            t_entry = team_dict.get(r['reviewer__id'], None)
            if t_entry:
                if type(t_entry) is list:
                    # if so, add number of members still on the team at the time of submission
                    for tpl in t_entry:
                        if r['time_submitted'] < tpl[1]:
                            pcnt += 1.0
            y[rev_index][bin_nr] += pcnt
    # calculate the cumulative counts
    for i in range(nr_of_steps + ce.final_reviews + 1):
        for b in range(1, present_bin + 1):
            y[i][b] += y[i][b - 1]
    # scale counts to percentages of # participants
    if p_count > 0:
        for i in range(nr_of_steps + ce.final_reviews + 1):
            for b in range(present_bin + 1):
                y[i][b] = 100.0 * y[i][b] / p_count
    # get a font
    fnt = ImageFont.truetype(os.path.join(settings.FONT_DIR, 'segoeui.ttf'), 16)
    # get colors (shades of TU Delft blue and teal)
    blues = blue_range(nr_of_steps)
    teals = teal_range(ce.final_reviews)
    # size of image
    canvas = (IMG_WIDTH, IMG_HEIGHT)
    img = Image.new('RGBA', canvas, (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    # draw horizontal and vertical axes
    draw.line([(V_AXIS_X - 3, H_AXIS_Y), (V_AXIS_X + BAR_CNT * BAR_WIDTH, H_AXIS_Y)],
        fill=(0, 0, 0, 255), width=1)
    draw.line([(V_AXIS_X, H_AXIS_Y+ 4), (V_AXIS_X, H_AXIS_Y - 250)],
        fill=(0, 0, 0, 255), width=1)
    # calculate how many pixels corresponds to one day
    pixels_per_day = 24.0 * 60.0 * 60.0 * BAR_WIDTH / time_step
    estafette_days = int(BAR_CNT * BAR_WIDTH / pixels_per_day)
    # draw ticks and day numbers
    three_digits = fnt.getsize('000')[0]
    dx = 0
    x = V_AXIS_X
    for d in range(1, estafette_days + 1):
        x += pixels_per_day
        draw.line([(x, H_AXIS_Y), (x, H_AXIS_Y + 4)], fill=(0, 0, 0, 255), width=1)
        # draw number only if x has advanced enough to allow 3 digits
        dx += pixels_per_day
        if dx >= three_digits:
            draw.text((x - fnt.getsize(str(d))[0] / 2.0, H_AXIS_Y + 4), str(d),
                font=fnt, fill=(0, 0, 0, 255))
            dx = 0
    draw.text(
        (V_AXIS_X - 15, H_AXIS_Y + 4),
        ce.course.language.phrase('Day'),
        font=fnt,
        fill=(0, 0, 0, 255)
        )
    # draw color legend
    lx = V_AXIS_X
    for l in range (nr_of_steps, -1, -1):
        draw.rectangle([lx, H_AXIS_Y + 29, lx + 20, H_AXIS_Y + 49],
            fill=blues[l], outline=None)
        draw.text((lx + 7, H_AXIS_Y + 27), str(nr_of_steps - l),
            font=fnt, fill=(128, 128, 128, 255))
        lx += 30
    for r in range (1, ce.final_reviews + 1):
        draw.rectangle([lx, H_AXIS_Y + 29, lx + 20, H_AXIS_Y + 49],
            fill=teals[ce.final_reviews - r], outline=None)
        draw.text((lx + 7, H_AXIS_Y + 27), str(r),
            font=fnt, fill=(128, 128, 128, 255))
        lx += 30
    r = (ce.course.language.phrase('Reviews') if ce.final_reviews > 0 else '')
    draw.text(
        (lx, H_AXIS_Y + 27),
        ce.course.language.phrase('Steps_completed').format(r),
        font=fnt,
        fill=(128, 128, 128, 255)
        )
    # draw step bars
    for l in range (nr_of_steps, -1, -1):
        x = V_AXIS_X + 1
        for b in range (0, present_bin + 1):
            if y[l][b] > 0:
                draw.rectangle(
                    [x, H_AXIS_Y - round(2.5*y[l][b]) - 1, x + BAR_WIDTH - 1, H_AXIS_Y - 1],
                    fill=blues[l], outline=None)
            x += BAR_WIDTH
    # draw final review bars
    for r in range (1, ce.final_reviews + 1):
        x = V_AXIS_X + 1
        for b in range (0, present_bin + 1):
            if y[nr_of_steps + r][b] > 0:
                draw.rectangle(
                    [x, H_AXIS_Y - 2.5*y[nr_of_steps + r][b] - 1,
                     x + BAR_WIDTH - 1, H_AXIS_Y - 1],
                    fill=teals[ce.final_reviews - r], outline=None)
            x += BAR_WIDTH
    # draw 20% lines in gray
    ly = H_AXIS_Y - 250
    for i in range(0, 5):
        draw.line(
            [(V_AXIS_X - 3, ly), (V_AXIS_X + BAR_CNT * BAR_WIDTH, ly)],
            fill=(200, 200, 200, 255),
            width=1
            )
        txt = '{}%'.format(100 - 20*i)
        draw.text(
            (V_AXIS_X - fnt.getsize(txt)[0] - 6, ly - 13),
            txt,
            font=fnt,
            fill=(0, 0, 0, 255)
            )
        ly += 50;
    # also draw 0% at bottom
    txt = '0%'
    draw.text(
        (V_AXIS_X - fnt.getsize(txt)[0] - 6, ly - 13),
        txt,
        font=fnt,
        fill=(0, 0, 0, 255)
        )
    # also draw number of participants (N) beneath the 100% mark
    txt = '(N = {})'.format(p_count)
    wh = fnt.getsize(txt)
    draw.rectangle(
        [V_AXIS_X + 4, H_AXIS_Y - 264, V_AXIS_X + 5 + wh[0], H_AXIS_Y - 260 + wh[1]],
        fill=(255, 255, 255, 255),
        outline=None
        )
    draw.text((V_AXIS_X + 5, H_AXIS_Y - 263), txt, font=fnt, fill=(0, 0, 0, 255))
    
    # get a small font for displaying the deadlines
    sfnt = ImageFont.truetype(os.path.join(settings.FONT_DIR, 'segoeui.ttf'), 12)

    if ce.bonus_per_step:
        # draw speed bonus deadlines in transparent magenta
        bd = ce.bonus_deadlines()
        for i in range(1, nr_of_steps + 1):
            # NOTE: use GET as dict may be empty or incomplete
            bdt = bd.get(i, None)
            if bdt:
                present_bin = min(
                    int((bdt - t_start).total_seconds() / time_step),
                    BAR_CNT
                    )
                x = V_AXIS_X + (present_bin + 1)* BAR_WIDTH
                draw.line(
                    [(x, H_AXIS_Y - 250), (x, H_AXIS_Y)],
                    fill=(161, 0, 88, 64),
                    width=1
                    )
                # convert datetime to two strings: date and time
                txt = bdt.strftime(DAY_TIME).split(' ')
                wh = sfnt.getsize(txt[0])
                draw.text(
                    (x - wh[0]/2, H_AXIS_Y - 265),
                    txt[0],
                    font=sfnt,
                    fill=(161, 0, 88, 128)
                    )
                wh = sfnt.getsize(txt[1])
                draw.text(
                    (x - wh[0]/2, H_AXIS_Y - 250),
                    txt[1],
                    font=sfnt,
                    fill=(161, 0, 88, 128)
                    )
            
    # draw assignment deadline in TU Delft magenta
    present_bin = min(int((ce.deadline - t_start).total_seconds() / time_step), BAR_CNT)
    x = V_AXIS_X + (present_bin + 1) * BAR_WIDTH
    draw.line([(x, H_AXIS_Y - 250), (x, H_AXIS_Y)], fill=(161, 0, 88, 255), width=1)
    # convert datetime to two strings: date and time
    tzi = timezone.get_current_timezone()
    txt = ce.deadline.astimezone(tzi).strftime(DAY_TIME).split(' ')
    wh = sfnt.getsize(txt[0])
    draw.text((x - wh[0]/2, H_AXIS_Y - 265), txt[0], font=sfnt, fill=(161, 0, 88, 255))
    wh = sfnt.getsize(txt[1])
    draw.text((x - wh[0]/2, H_AXIS_Y - 250), txt[1], font=sfnt, fill=(161, 0, 88, 255))
    # draw reviews deadline in TU Delft orange
    present_bin = min(int((ce.review_deadline - t_start).total_seconds() / time_step), BAR_CNT)
    x = V_AXIS_X + (present_bin + 1) * BAR_WIDTH
    draw.line([(x, H_AXIS_Y - 250), (x, H_AXIS_Y)], fill=(236, 127, 44, 255), width=1)
    # convert datetime to two strings: date and time
    txt = ce.review_deadline.astimezone(tzi).strftime(DAY_TIME).split(' ')
    wh = sfnt.getsize(txt[0])
    draw.text((x - wh[0]/2, H_AXIS_Y - 265), txt[0], font=sfnt, fill=(236, 127, 44, 255))
    wh = sfnt.getsize(txt[1])
    draw.text((x - wh[0]/2, H_AXIS_Y - 250), txt[1], font=sfnt, fill=(236, 127, 44, 255))
    # return the image
    return img


# returns a list of n shades of TU Delft blue from dark to light
def blue_range(n):
    if n <= 1:
        return ['#00a6f0', '#ebebeb']
    tud_blue = [0, 166, 240]  # to be middle of the color range
    dark_blue = [15, 17, 80]
    light_blue = [198, 238, 250]
    if n % 2:
        # for an odd number of colors, TUD blue is central color
        tud = [tud_blue]
        m = 2.0 / (n - 1) 
    else:
        # for an even number, TUD blue is "aimed for", but not reached
        tud = []
        m = 2.0 / n
    light = [
        [round(198 - i*m*198), round(238 - i*m*72), round(250 - i*m*10)]
            for i in range(math.trunc(n / 2) - 1, -1, -1)
        ]
    dark = [[round(15 - i*m*15), round(17 + i*m*149), round(80 + i*m*160)]
            for i in range(math.trunc(n / 2))
        ]
    # registration color is a light shade of grey
    blues = dark + tud + light + [[235, 235, 235]]
    return ['#' + ''.join(['{:02x}'.format(r) for r in c]) for c in blues]


# returns a list of n shades of TU Delft teal from dark to light
def teal_range(n):
    if n <= 1:
        return ['#66bcaa']
    dark_teal = [40, 90, 80]  # to be the end of the range
    tud_teal = [102, 188, 170]
    m = 1 / (n - 1)
    teals = [[round(40 + i*m*62), round(90 + i*m*98), round(80 + i*m*90)]
            for i in range(n)
        ]
    return ['#' + ''.join(['{:02x}'.format(int(r)) for r in c]) for c in teals]

