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

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.utils import IntegrityError

from presto.models import Assignment, Language, LegVideo, Role, UserDownload, DEFAULT_DATE

from presto.uiphrases import UI_LANGUAGE_CODES, UI_LANGUAGE_NAMES

# populates database with generic data
class Command(BaseCommand):

    def handle(self, *args, **options):
        print 'Initializing data...'

        # create supported languages
        for i in range(len(UI_LANGUAGE_CODES)):
            l, cr_l = Language.objects.get_or_create(
                name=UI_LANGUAGE_NAMES[i], code=UI_LANGUAGE_CODES[i])
            if cr_l:
                print 'Added language: %s' % unicode(l)

        # create groups
        Role.objects.get_or_create(name='Student', rank=1, icon='user')
        Role.objects.get_or_create(name='Instructor', rank=2, icon='student')
        Role.objects.get_or_create(name='Developer', rank=3, icon='cubes')
        Role.objects.get_or_create(name='Administrator', rank=4, icon='user circle')
        print 'User groups created.'
        
        # create video clip references
        videos = [
            {'n': 0, 'r': 0, 'l': en, 'p': 'PB', 'u': 'https://www.youtube.com/embed/GGfLFjDr0X4'},
            {'n': 1, 'r': 1, 'l': en, 'p': 'PB', 'u': 'https://www.youtube.com/embed/zmv7dzTAaFU'},
            {'n': 2, 'r': 1, 'l': en, 'p': 'JS', 'u': 'https://www.youtube.com/embed/9888ufSRsps'},
            {'n': 3, 'r': 1, 'l': en, 'p': 'EvD', 'u': 'https://www.youtube.com/embed/aubP8M4CMA0'},
            {'n': 4, 'r': 1, 'l': en, 'p': 'FM', 'u': 'https://www.youtube.com/embed/_wavPpOivgo'},
            {'n': 5, 'r': 1, 'l': en, 'p': 'SD', 'u': 'https://www.youtube.com/embed/3OuOqmUqDOk'},
            {'n': 6, 'r': 1, 'l': en, 'p': 'PB', 'u': 'https://www.youtube.com/embed/7qZD4IRZ2ek'},
            {'n': 1, 'r': 2, 'l': en, 'p': 'PB', 'u': 'https://www.youtube.com/embed/mS_J-Kyqy6I'},
            {'n': 2, 'r': 2, 'l': en, 'p': 'JS', 'u': 'https://www.youtube.com/embed/SM_xMe9kH9w'},
            {'n': 3, 'r': 2, 'l': en, 'p': 'EvD', 'u': 'https://www.youtube.com/embed/KaktyAtoOUM'},
            {'n': 4, 'r': 2, 'l': en, 'p': 'FM', 'u': 'https://www.youtube.com/embed/yEC1kmlh6mg'},
            {'n': 5, 'r': 2, 'l': en, 'p': 'SD', 'u': 'https://www.youtube.com/embed/hAgmxKWT5_M'},
            {'n': 6, 'r': 2, 'l': en, 'p': 'PB', 'u': 'https://www.youtube.com/embed/I4_goXCcIe0'},
            {'n': 1, 'r': 1, 'l': nl, 'p': 'PB', 'u': 'https://www.youtube.com/embed/WmY41X1MOIo'},
            {'n': 2, 'r': 1, 'l': nl, 'p': 'FM', 'u': 'https://www.youtube.com/embed/yBKgZKVX4J4'},
            {'n': 3, 'r': 1, 'l': nl, 'p': 'EvD', 'u': 'https://www.youtube.com/embed/yf7b2T-mcEM'},
            {'n': 4, 'r': 1, 'l': nl, 'p': 'FM', 'u': 'https://www.youtube.com/embed/ySBHGscPmUs'},
            {'n': 5, 'r': 1, 'l': nl, 'p': 'SD', 'u': 'https://www.youtube.com/embed/K_0B04t0C3w'},
            {'n': 6, 'r': 1, 'l': nl, 'p': 'PB', 'u': 'https://www.youtube.com/embed/HUCzBWcV6qA'},
            {'n': 1, 'r': 2, 'l': nl, 'p': 'PB', 'u': 'https://www.youtube.com/embed/2sD0h3GMQMc'},
            {'n': 2, 'r': 2, 'l': nl, 'p': 'FM', 'u': 'https://www.youtube.com/embed/Vlzk__Ho49Q'},
            {'n': 3, 'r': 2, 'l': nl, 'p': 'EvD', 'u': 'https://www.youtube.com/embed/bWY1HWwbguk'},
            {'n': 4, 'r': 2, 'l': nl, 'p': 'FM', 'u': 'https://www.youtube.com/embed/Qcdrk8y6JSg'},
            {'n': 5, 'r': 2, 'l': nl, 'p': 'SD', 'u': 'https://www.youtube.com/embed/KQo9Ule7S1U'},
            {'n': 6, 'r': 2, 'l': nl, 'p': 'PB', 'u': 'https://www.youtube.com/embed/b1kfbX13ufk'}
        ]
        n = 0
        for v in videos:
            try:
                lv, cr = LegVideo.objects.get_or_create(leg_number=v['n'], star_range=v['r'],
                    language=v['l'], presenter_initials=v['p'], url=v['u'])
                if cr:
                    n += 1
            except Exception, e:
                print 'Problem with video %s: %s' % (unicode(v), str(e))
        if n > 0:
            print 'Added %d video clips' % n

        print 'Done.'

#        # EXAMPLE of how to add records to database using "raw" SQL
#        with connection.cursor() as cursor:
#            cursor.execute("INSERT INTO `presto_assignment` VALUES "
#                + "(...), (...), ..."
#            )
