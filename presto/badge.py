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
from django.db.models import Count
from django.http import HttpResponse
from django.utils import timezone
from django.utils.timezone import localtime

from .models import PrestoBadge, DEFAULT_DATE

# python modules
from binascii import hexlify
from datetime import datetime
from hashlib import pbkdf2_hmac

import json
import math
import os
from PIL import Image, ImageDraw, ImageFont
from random import randint
from tempfile import mkstemp
from time import sleep

# presto modules
from presto.generic import change_role, generic_context, has_role
from presto.utils import decode, encode, log_message, prefixed_user_name

BADGE_METALS = ['brass', 'bronze', 'copper', 'gold', 'silver', 'steel']

GRAD_IMG = 'runner-gradient.png'
REF_GRAD_IMG = 'referee-gradient.png'
WREATH_IMG = 'wreath.png'


# NOTE: the points have been determined by hand based on a drawing; the factor 0.2575
#       scales the star to fit in the 130 pixels wide band of a standard relay badge
STAR_POLYGON = [(0.2575*x, 0.2575*y) for x, y in [(0, -280), (65, -90), (265, -90), (105, 35),
    (165, 225), (0, 110), (-165, 225), (-105, 35), (-265, -90), (-65, -90)]]

BADGE_WIDTH = 256
BADGE_HEIGHT = 256

# NOTE: Data that can be stored on a badge is limited not only by the 256x256 badge size,
#       but also the need to NOT use (semi)transparent pixels because these tend to be altered
#       during copy/paste operations. Hence, we only use the inner square of the badge disc,
#       which is 175x175 pixels. This would leave 30625 bits, but for additional security
#       we use it a bit sparsely. 16127 happens to be the largest prime number < 30625,
#       so that provides a convenient MODULUS for a deterministic random walk sequence.
#       Since we need 256 bits for a hash signature and 14 for the data bit count, this limits
#       the usable storage to 16127 - 270 = 15857 bits, which we round down to 1982 bytes.
MAX_DATA_BITS = 1982*8

# NOTE: the present algorithm provides only weak security! you may want to customize your encoding 
SECRET_SEED = 8888
LOW_PRIME = 7919
HIGH_PRIME = 16127

# define a list of 16127 pseudo-random points (x, y) located in a square 175x175 square
# having (127, 127) as its center
PIXEL_POINTS = [(0, 0)] * HIGH_PRIME
n = SECRET_SEED
for i in range(HIGH_PRIME):
    x, y = divmod(n, 127)
    # add (40, 40) to make (127, 127 the actual center)
    PIXEL_POINTS[i] = (40 + int(x * 1.37771), 40 + int(y * 1.37771))
    n = (n * LOW_PRIME) % HIGH_PRIME


# returns a tuple (disc image file name, (red, green, blue, alpha)) for a given "badge_color"
def disc_and_color(bc):
    # badge color is encoded in lower 4 bytes: disc number (highest), red , green, blue (lowest)
    bc, blue = divmod(bc & 0xffffffff, 256)
    bc, green = divmod(bc, 256)
    disc, red = divmod(bc, 256)
    # odd disc numbers indicate dark metal shades
    disc, dark = divmod(disc, 2)
    # protect against disc numbers beyond range
    disc = disc % len(BADGE_METALS)
    return ('disc-%s%s.png' % (BADGE_METALS[disc], '-dark' if dark else ''), (red, green, blue, 255))


# returns star polygon coordinates for M-th star of in total N stars (zero-based!)
# NOTE: assumes 1440x1440 pixel bitmap; can hold up to 21 stars, but referee badges only up to 10
def star_polygon(m, n, radius):
    # angle for first star = (N-1)/2 * PI/10  (NOTE: PI = 3 to squeeze stars in a bit)
    angle = 0.15 * (n - 1) - m * 0.3
    sin_a = math.sin(angle)
    cos_a = math.cos(angle)
    center_x = 720.0 - sin_a * radius
    center_y = 720.0 - cos_a * radius
    star = [(center_x + cos_a*x + sin_a*y, center_y - sin_a*x + cos_a*y) for x, y in STAR_POLYGON]
    return star


# returns a PIL image for an n-star participant badge image with color bc
def participant_badge_image(n, bc):
    # convert badge color (integer) to disc image file and RGBA tuple
    d, c = disc_and_color(bc)
    # start with the disc image
    img = Image.open(os.path.join(settings.BADGE_DIR, d))
    draw = ImageDraw.Draw(img)
    # then draw the colored arc
    if n <= 0:
        start_angle = 0
        end_angle = 2*math.pi
    else:
        start_angle = 0.55*math.pi + (n - 1)*0.15
        end_angle = 2.45*math.pi - (n - 1)*0.15
    # as PIL's arc is one pixel thin, approximate the arc as a 500-point polyline
    alpha = start_angle
    delta = (end_angle - start_angle) / 500
    points = []
    for i in range(500):
        # NOTE: 630 = 720 - 90 px (disc radius minus distance of colored line from rim)
        points.append((720 + 630*math.cos(alpha), 720 - 630*math.sin(alpha)))
        alpha += delta
    draw.line(points, fill=c, width=8)
    # draw the inner disc
    draw.ellipse((172, 172, 1268, 1268), fill=c)
    # draw the stars
    for i in range(0, n):
        draw.polygon(star_polygon(i, n, 630), fill=c)
    # overlay it with the icon image (this also adds the gradient)
    icon_img = Image.open(os.path.join(settings.BADGE_DIR, GRAD_IMG))
    img = Image.alpha_composite(img, icon_img)
    # resize the image to 256x256 pixels
    img = img.resize((BADGE_WIDTH, BADGE_HEIGHT), Image.BICUBIC)
    return img


# returns a PIL image for a level n referee badge image with color bc
def referee_badge_image(n, bc):
    # convert badge color (integer) to disc image file and RGBA tuple
    d, c = disc_and_color(bc)
    # start with the disc image
    img = Image.open(os.path.join(settings.BADGE_DIR, d))
    # create the wreath image
    w_img = Image.open(os.path.join(settings.BADGE_DIR, WREATH_IMG))
    paste_img = Image.new('RGBA', (1440, 1440), color=c)
    img.paste(paste_img, mask=w_img)
    draw = ImageDraw.Draw(img)
    # disc rim in badge color
    draw.ellipse((260, 260, 1180, 1180), fill=c)
    # narrow white band to create a double rim
    draw.ellipse((276, 276, 1164, 1164), fill=(255, 255, 255, 255))
    # inner disc in badge color
    draw.ellipse((284, 284, 1156, 1156), fill=c)
    # draw the stars
    for i in range(0, n):
        # NOTE: on referee badge, stars are drawn 30 px further from the disc edge
        draw.polygon(star_polygon(i, n, 590), fill=c)
    # overlay it with the icon image (this also adds the gradient)
    icon_img = Image.open(os.path.join(settings.BADGE_DIR, REF_GRAD_IMG))
    img = Image.alpha_composite(img, icon_img)
    # resize the image to 256x256 pixels
    img = img.resize((BADGE_WIDTH, BADGE_HEIGHT), Image.BICUBIC)
    return img


# creates a PNG image for a badge and pushes it to the browser
def render_sample_badge(bc):
    img = participant_badge_image(3, bc)
    # output image to browser (do NOT save it as a file)
    response = HttpResponse(content_type='image/png')
    img.save(response, 'PNG')
    return response


# creates a 80x80 px PNG image for a badge and pushes it to the browser
def render_tiny_badge_image(badge):
    # get the badge image
    if badge.participant:
        img = participant_badge_image(badge.attained_level, badge.course.badge_color)
    elif badge.referee:
        img = referee_badge_image(badge.attained_level, badge.course.badge_color)
    else:
        raise ValueError('Undefined badge owner')
    # resize the image to 80x80 pixels
    img = img.resize((80, 80), Image.BICUBIC)
    # output image to browser (do NOT save it as a file)
    response = HttpResponse(content_type='image/png')
    img.save(response, 'PNG')
    return response


# creates a certified PNG image for a badge and pushes it to the browser
def render_certified_badge(badge):
    # capture and log any error that may occur
    try:
        # get the badge image
        if badge.participant:
            img = participant_badge_image(badge.attained_level, badge.course.badge_color)
        elif badge.referee:
            img = referee_badge_image(badge.attained_level, badge.course.badge_color)
        else:
            raise ValueError('Undefined badge owner')
        # spray about 50% of the image with noise
        pix = img.load()
        for y in range(0, BADGE_HEIGHT):
            for x in range(0, BADGE_WIDTH):   
                if randint(0, 1):
                    wipe_bit(pix, x, y)
        # get the badge as dictionary
        bd = badge.as_dict()
        # encode it as a string of '0' and '1'
        data_bits = dict_to_binary(bd)
        # throw an exception if data to be stored exceeds 16 thousand bits
        bit_count = len(data_bits)
        if bit_count > MAX_DATA_BITS:
            raise ValueError('Badge data exceeds %d bytes' % MAX_DATA_BITS // 8)
        # compute a hash (for validation purposes) and render it as string of '0' and '1'
        bits_hash = hash_to_binary(hexlify(pbkdf2_hmac("sha256", data_bits,
                settings.BADGE_SALT, settings.BADGE_ITERATIONS)))
        # throw an exception if hash is not exactly 256 bits
        if len(bits_hash) != 256:
            raise ValueError('Badge signature is not 256 bits')
        # write the hash in the first 256 "random" pixels
        for i, b in enumerate(bits_hash):
            code_bit(pix, i, b)
        # write the bit string length in the next 14 pixels (2^14 - 1 = 16385 suffices)
        bc_bits = format(bit_count, '014b')
        for i, b in enumerate(bc_bits):
            code_bit(pix, 256 + i, b)
        # then write the badge data bits
        for i, b in enumerate(data_bits):
            code_bit(pix, 270 + i, b)
        # update the rendering parameters
        badge.time_last_rendered = timezone.now()
        badge.rendering_count += 1
        badge.save()
        log_message('Rendered this badge: ' + unicode(badge))
        # output image to browser (do NOT save it as a file)
        response = HttpResponse(content_type='image/png')
        img.save(response, 'PNG')
        return response
    except Exception, e:
        log_message('Failed to render badge: ' + str(e))
        return None


# returns a PrestoBadge object identified by the data found in the img object,
# or FALSE if that image is not valid
def verify_certified_image(img):
    try:
        # make pixels accessible as pix[x, y]
        pix = img.load()
        w, h = img.size
        # check for approriate dimensions
        if h != BADGE_HEIGHT or w != BADGE_WIDTH:
            raise ValueError('Badge should be 256x256 pixels')
        # get the 256-bit signature
        signature = ''.join([test_bit(pix, i) for i in range(0, 256)])
        # get the length of the "payload" coded in the next 14 bits
        bits = ''.join([test_bit(pix, i) for i in range(256, 270)])
        bit_count = int(bits, 2)
        if bit_count > MAX_DATA_BITS:
            raise ValueError('Invalid data size (%d)' % bit_count)
        # get the actual data
        bits = ''.join([test_bit(pix, i) for i in range(270, 270 + bit_count)])
        # check integrity of bits
        bits_hash = hash_to_binary(hexlify(pbkdf2_hmac("sha256", bits,
                settings.BADGE_SALT, settings.BADGE_ITERATIONS)))
        if bits_hash != signature:
            raise ValueError('Corrupted badge data')
        # decode the bits
        bd = binary_to_dict(bits)
        # see if the standard badge properties exist
        mf = list(set(['ID', 'CC', 'CN', 'AL', 'TI', 'PR', 'FN', 'EM']) - set(bd.keys()))
        if mf:
            raise ValueError('Incomplete data (missing: %s)' % ', '.join(mf))
        # see if the badge exists in the database
        # NOTE: use filter instead of get so that we can generate our own error message
        b = PrestoBadge.objects.filter(pk=bd['ID'])
        if b.count() == 0:
            raise ValueError('Unmatched badge ID')
        # get the first element (should be the only one)
        b = b.first()
        if b.participant:
            u = b.participant.student.user
            pr = b.participant.estafette.estafette.name
        if b.referee:
            u = b.referee.user
            pr = b.referee.estafette_leg.template.name
        # see if badge data match those in database
        if prefixed_user_name(u) != bd['FN']:
            raise ValueError('Holder name (%s) does not match "%s"' %
                (bd['FN'], prefixed_user_name(u)))
        if u.email != bd['EM']:
            raise ValueError('Holder e-mail address (%s) does not match "%s"' %
                (bd['EM'], u.email))
        if b.course.code != bd['CC']:
            raise ValueError('Course code (%s) does not match "%s"' % (bd['CC'], b.course.code))
        if b.course.name != bd['CN']:
            raise ValueError('Course name (%s) does not match "%s"' % (bd['CN'], b.course.name))
        if pr != bd['PR']:
            raise ValueError('Project relay name (%s) does not match "%s"' %
                (bd['PR'], pr))
        if b.attained_level != bd['AL']:
            raise ValueError('Attained level (%d) should have been %d' % (bd['AL'], b.attained_level))
        # update badge verification parameters
        b.time_last_verified = timezone.now()
        b.verification_count += 1
        b.save()
        # return the badge object
        return b
    except Exception, e:
        log_message('Failed to validate badge: ' + str(e))
        return False


# view for badge "page"
# NOTE: this view does not render a page, but sends a PNG file to the browser
@login_required(login_url=settings.LOGIN_URL)
def badge(request, **kwargs):
    # NOTE: a downloaded image is part the current page, meaning that the coding keys
    # should NOT be rotated; this is achieved by passing "NOT" as test code.
    context = generic_context(request, 'NOT')
    try:
        # check whether user can have student role
        if not (has_role(context, 'Student') or has_role(context, 'Instructor')):
            raise Exception('No access')

        # if a sample badge is asked for, render it in the requested color
        bc = kwargs.get('bc', '')
        if bc:
            # render a participant badge (image only, not certified)
            return render_sample_badge(int(bc))
        
        # otherwise, a hex-encoded badge ID is needed
        h = kwargs.get('hex', '')
        # verify that hex code is valid
        # NOTE: since keys have not been rotated, use the ENcoder here!
        bid = decode(h, context['user_session'].encoder)
        b = PrestoBadge.objects.get(pk=bid)
        # for speed, the reward gallery requests tiny images (80x80 px)
        if kwargs.get('tiny', ''):
            return render_tiny_badge_image(b)
        # if otherwise render the certified badge image
        return render_certified_badge(b)
    
    except Exception, e:
        log_message('ERROR while rendering badge: %s' % str(e), context['user'])
        with open(os.path.join(settings.IMAGE_DIR, 'not-found.png'), "rb") as f:
            return HttpResponse(f.read(), content_type="image/png")


# AUXILIARY FUNCTIONS

# returns a string of 256 binary digits representing the value of the 64-digit hexadecimal string h
def hash_to_binary(h):
    return format(int(h, 16), '0256b')


# encodes a dict as a binary string
def dict_to_binary(dictio):
    jsn_str = json.dumps(dictio)
    bin_str = ''.join(format(ord(c), '08b') for c in jsn_str)
    return bin_str


# decodes a dictionary from a binary string
def binary_to_dict(bin_str):
    jsn_str = ''.join(chr(int(bin_str[i:i+8], 2)) for i in xrange(0, len(bin_str), 8))
    dictio = json.loads(jsn_str)  
    return dictio


# randomly alters the low RGB bits of the pixel (this is used for masking purposes)
def wipe_bit(pix, x, y):
    # convert tuple to list
    p = list(pix[x, y])
    # randomly alter lowest RGB bits
    r = randint(0, 3)
    for i in range(3):
        p[i] = p[i] ^ ((r >> i) & 1)
    # update the pixel in the image
    pix[x, y] = tuple(p)


# codes the i-th pixel point of the random walk for the specified bit value ('0' or '1')
def code_bit(pix, i, bit):
    # get the point coordinates
    x = PIXEL_POINTS[i][0]
    y = PIXEL_POINTS[i][1]
    # convert tuple to list
    p = list(pix[x, y])
    # randomly alter lowest RGB bits (NOTE: calling wipe_bit would be slower)
    r = randint(0, 3)
    for i in range(3):
        p[i] = p[i] ^ ((r >> i) & 1)
    # the pixel to be used depends on lower bits of X and Y
    i = (x % 2) + (y % 2)
    # code this bit using only the low bit of the specified bit value
    p[i] = (p[i] & 254) | (int(bit) & 1)
    # update the pixel in the image
    pix[x, y] = tuple(p)


# returns the decoded bit value of the i-th pixel of the random walk as '0' or '1'
def test_bit(pix, i):
    # get the point coordinates
    x = PIXEL_POINTS[i][0]
    y = PIXEL_POINTS[i][1]
    p = pix[x, y]
    # the pixel to be tested depends on lower bits of X and Y
    i = (x % 2) + (y % 2)
    if p[i] & 1:
        return '1'
    return '0'


