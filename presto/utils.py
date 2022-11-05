"""
General utility functions used by other Presto modules.

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

import io
import os
import re
import subprocess

from datetime import date, datetime, time, timedelta
from hashlib import md5
from math import fabs, modf
from random import randrange
from string import hexdigits

# frequently used constants
DATE_TIME_FORMAT = '%A, %d %B %Y %H:%M'
DATE_FORMAT = '%A, %d %B %Y'
EDIT_STRING = 'Last edited by {name} on {time}.'
GRACE_MINUTE = timedelta(seconds=60)

# NOTE: session keys are tested in three stages:
#       (1) not the required 32 hex digit format => incorrect
#       (2) integrity checks fail => inconsistent
#       (3) no encoder/decoder match => expired
EXPIRED_SESSION_KEY = 'Your session has expired'
INCONSISTENT_SESSION_KEY = 'Inconsistent session key'
INCORRECT_SESSION_KEY = 'Incorrect session key'

# Semantic UI icon names expressing opinions:
FACES = [
    'grey question circle outline',
    'smile outline',
    'meh outline',
    'frown outline',
    'pointing up outline',
    'pointing down outline',
    'pointing left outline',
    'pointing right outline',
    'handshake outline'
    ]

# Colors to mark decision appreciation segments:
COLORS = ['', 'green', 'yellow', 'red']

# UI phrase keys expressing opinions:
OPINIONS = ['ERROR', 'Quite_happy', 'Mixed_feelings', 'Unhappy']
YOUR_OPINIONS = ['ERROR', 'You_quite_happy', 'Mixed_feelings', 'You_unhappy']
IMPROVEMENTS = ['Pass', 'No_improvement', 'Minor_changes', 'Good_job']


# infers last name prefix of user from TU Delft e-mail address
def prefixed_user_name(user):
    if not user:
        return ''
    if user.first_name == 'Presto' and user.last_name == 'Administrator':
        return user.get_full_name()
    e = user.email.split('@')
    # assume that only TU Delft uses the e-mail format INITIALS-prefix-LAST NAME
    if len(e) < 2 or 'tudelft.nl' not in e[1]:
        return user.get_full_name()
    # strip initials, split at upper case characters, and retain the leading lower case string
    n = e[0].strip('0123456789-').split('.')[-1]
    p = ''
    i = 0
    while i < len(n) and n[i] == n[i].lower():
        p += n[i]
        i += 1
    if p:
        p = p.replace('van', 'van ')
        if p[-1] == 't':
            p = p[:-1] + "'t"
        if p == 'd':
            p = "d'"
        elif p[-1] != ' ':
            p += ' '
    # NOTE: for some students, their first name also included their last name (data entry error?)
    #       so check if last name is identical to right part of first name of equal length
    fn = user.first_name
    ln = user.last_name
    if fn[-len(ln):] == ln:
        fn = fn.replace(ln, '').strip()
    return fn + ' ' + p + ln    


# writes message to log file.
def log_message(msg, user=None):
    dt = datetime.now().strftime('%Y-%m-%d  %H:%M:%S')
    usr = 'anonymous' if user is None else prefixed_user_name(user)
    log_line = '{} [{}] [{}] {}\n'.format(dt, settings.USER_IP, usr, msg)
    # print log_line
    path = os.path.join(
        settings.LOG_DIR,
        'presto-' + datetime.today().strftime('%Y%m%d') + '.log'
        )
    with io.open(path, 'a+', encoding='utf-8') as logfile:
        logfile.write(log_line)


# generates a string with $n random hexadecimal digits.
def random_hex(n=16):
    return format(randrange(0, 1 << (n*4)), 'x').zfill(n)


# encodes a 64-bit integer n as a 32 hex digit string using a 32 hex digit key k as mask
# NOTE: if deterministic=True, the encoding should not include random elements
def encode(n, k, deterministic=False):
    # first convert integer to 16-digit hexadecimal string
    s = format(n, 'x').zfill(16)
    # then to a 16-entry 0-based array of integer (0-15)
    hx = []
    for c in s:
        hx.append(int(c, 16))
    # also convert the 32-digit session key to a 0-based array of integer (0-15)
    key = []
    for c in k:
        key.append(int(c, 16))
    # hx and key now both hold nibbles as integer values
    # code will hold 32 encoded digits in pseudo-random order
    code = {}
    # p serves as starting point for pseudo-random sequences (CANNOT BE ZERO!)
    if deterministic:
        p = 15
    else:
        p = randrange(1, 16)
    # this seed will be the first digit of the encoded number
    code[0] = format(p, 'x')
    # start the random walk
    q = p
    for i in range (1, 17):
        p = (p * 199) % 31
        q = (q * 197) % 17
        code[p] = format(hx[q - 1] ^ key[p], 'x')  # xor with mask
    for i in range(17, 31):
        p = (p * 199) % 31
        q = (q * 197) % 17
        r, odd = divmod(i, 2)
        if odd:
            # odd digits are "fillers"
            if deterministic:
                code[p] = format(r & 15 ^ 11, 'x')
            else:
                # random value (to add noise to the code)
                code[p] = format(randrange(0, 15), 'x')
        else:
            # 7 even digits of the code are duplicate hx values that will be used for validation
            code[p] = format(hx[q - 1] ^ key[p], 'x')
    # count the number of set bits (1's) in the first 31 hex digits
    sb = {'0': 0, '1': 1, '2': 1, '3': 2, '4': 1, '5': 2, '6': 2, '7': 3,
          '8': 1, '9': 2, 'a': 2, 'b': 3, 'c': 2, 'd': 3, 'e': 2, 'f': 4}
    b = 0
    for c in code.itervalues():
        b += sb[c]
    # store this count (modulo 16) as the last hex digit to allow data integrity checking
    code[31] = format(b % 16, 'x')
    # string the digits together in the order of their dictionary index
    return ''.join(code[c] for c in sorted(code))


# decodes an encoded 64-bit integer from an encoded 32 hex digit string s
# using 32 hex digit string k as key.
def decode(s, k):
    # reject strings that ar not 32-digit hexadecimal strings 
    if (len(s) != 32) or (all(c in hexdigits for c in s) == False):
        raise ValueError(INCORRECT_SESSION_KEY)
    # convert characters to numbers while counting the 1-bits
    sb = [0, 1, 1, 2, 1, 2, 2, 3, 1, 2, 2, 3, 2, 3, 2, 4]
    b = 0
    hx = []
    for c in s:
        i = int(c, 16)
        b += sb[i]
        hx.append(i)
    # check data integrity: # of 1-bits (modulo 16) of first 31 nibbles
    # should equal the value of the last hex digit
    if (b - sb[hx[31]]) % 16 != hx[31]:
        raise ValueError(INCONSISTENT_SESSION_KEY)
    key = []
    for c in k:
        key.append(int(c, 16))
    # hx and key now hold nibbles as integer values
    number = {}  # will hold 16 hex digits of the encoded number
    p = hx[0]
    q = p
    for i in range(1, 17):
        p = (p * 199) % 31
        q = (q * 197) % 17
        number[q - 1] = format(hx[p] ^ key[p], 'x')
    for i in range(17, 31):  # ignore the 32nd digit, as it is noise
        p = (p * 199) % 31
        q = (q * 197) % 17
        if i % 2 == 0:
            # the even nibbles should match; the odd ones are noise
            if number[q - 1] != format(hx[p] ^ key[p], 'x'):
                raise ValueError(EXPIRED_SESSION_KEY)
    return int(''.join(number[c] for c in sorted(number)), 16)


# for testing purposes only: compare random number with the result of decoding its encoding
def test_encoding(n):
    a = []
    f = 0
    k = random_hex(32)
    for i in range(1, n+1):
        r = i #randrange(0, 9999999)
        e = encode(r, k)
        d = decode(e, k)
        if d != r:
            a.append((r, e, d))
            f += 1
    return str(f) + ' encoding failures:' + str(a)


# returns a 32 hex digit string based on the current date and the passed parameter
def day_code(x):
    return md5((date.today().strftime("%d%m%Y%m%d") + str(x)) * 23).hexdigest()


# converts a date (+ time) string to a datetime value by trying out different patterns
def string_to_datetime(s):
    patterns = [
        '%Y-%m-%d %H:%M', '%d-%m-%Y %H:%M',
        '%Y-%b-%d %H:%M', '%d-%b-%Y %H:%M',
        '%Y %b %d %H:%M', '%d %b %Y %H:%M',
        '%Y-%m-%d', '%d-%m-%Y',
        '%Y-%b-%d', '%d-%b-%Y',
        '%Y %b %d', '%d %b %Y',
        '%m/%d/%Y %H:%M', '%m/%d/%Y'  # slashes indicate U.S. notation month/day/year
    ]
    for p in patterns:
        try:
            t = datetime.strptime(s, p)
            return str(t)[0:16]
        except:
            pass
    # return empty string if string s matches none of the patterns
    return ''


# converts a path that may mix \ (Windows) and / (Unix) to the active OS format
def os_path(path):
    # split the path on both slashes  and backslashes
    path = re.compile(r"[\/]").split(path)
    # join the path using the correct slash symbol:
    return os.path.join(*path)


def half_points(f):
    """
    Returns a string with float rounded to nearest 0,5 written as a fraction.

    Uses HTML entity &frac12; to denote for 1/2.
    Ignores the sign, i.e., uses the absolute value of f.
    """
    fp, ip = modf(fabs(float(f)))
    w = '' if ip == 0 else str(int(ip))
    h = '&frac12;' if 0.25 <= fp < 0.75 else ''
    return w + h


# half_points with explicit sign (i.e., + or -) if non-zero
def signed_half_points(f):
    if abs(f) < 0.25:
        return '0'
    return ('+' if f > 0 else '-') + half_points(f)


# like signed_half_points, but returns empty string for 0
def half_points_if_any(f):
    if abs(f) < 0.25:
        return ''
    return signed_half_points(f)


# returns disk usage for directory "path" in kilobytes (as a string)
def disk_usage(path):
    try:
        return subprocess.check_output(['du','-sh', path]).split()[0].decode('utf-8')
    except:
        return ''


# returns number n followed by phrase, which is pluralized unless n = 1  
def plural_s(n, phrase):
    if n == 1:
        return '1 ' + phrase
    return '{} {}s'.format(n, phrase)


# converts a positive integer into a base36 string
# NOTE: to decode it, use int(num, 36)
def int_to_base36(num):
    assert num >= 0
    digits = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    res = ''
    while not res or num > 0:
        num, i = divmod(num, 36)
        res = digits[i] + res
    return res


# returns the number of words (substrings without whitespace) in a string
def word_count(s):
    # NOTE: first replace </p> by a space, or </p><p> is not seen as a word separator
    s = re.sub(r'</p>', ' ', s)
    # then trim all other HTML tags
    s = re.sub(r'<.*?>', '', s).strip()
    if s:
        return len(s.split())
    return 0


def ui_img(s):
    return s.replace('<img ', '<img class="ui large image" ')


def pdf_to_text(path):
    """
    Extract text from PDF as 7-bit ASCII.
    """
    try:
        # On Windows, change to the directory where the application is
        # installed, or check_output throws an "Access denied" error.
        cwd = ''
        if settings.PDF_TO_TEXT_DIR:
            # save corrent working directory
            cwd = os.getcwd()
            # temporarily move to the directory containing pdftotext.exe
            os.chdir(settings.PDF_TO_TEXT_DIR)
            
        cmd = [settings.PDF_TO_TEXT_CMD, '-enc', 'ASCII7', path, '-']
        ascii = subprocess.check_output(cmd)

        # If changed, change back to the original current working directory.
        if cwd:
            os.chdir(cwd)

        # Remove all footers, assuming that these are single short lines
        # (typically "Page #" or just "#") that immediately preced a page
        # separator (form feed).
        pages = ascii.split('\f')
        ascii = ''
        # See what line separator is used.
        if pages:
            newline = '\r\n'
            if not (newline in pages[0]):
                newline = '\n'
        # Add page text without footer text.
        for p in pages:
            pars = p.split(newline)
            # Discard trailing blank lines.
            while pars and len(pars[-1]) == 0:
                pars.pop()
            # Discard last line if it is short.
            if (len(pars) > 1 and len(pars[-1]) < 20):
                pars.pop()
            # Add remaining paragraphs to result (using Unix newline).
            ascii += '\n'.join(pars)
            
    except Exception as e:
        log_message(
            'ERROR: Failed to execute command line {}\n{}'.format(
                ' '.join(cmd),
                str(e)
                )
            )
    return ascii
