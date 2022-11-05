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
from django.core.management.base import BaseCommand
from django.utils import timezone

from presto.models import Assignment, CourseEstafette, EstafetteCase, DEFAULT_DATE
from presto.utils import log_message

# this command is defined to test a routine -- put test code in the handle() routine
class Command(BaseCommand):

    def handle(self, *args, **options):
        aid = 17604
        case_letter = 'D'
        a = Assignment.objects.filter(id=aid).first()
        c = EstafetteCase.objects.filter(estafette=a.case.estafette, letter=case_letter).first()
        if a:
            log_message(
                'TRACE: Changing case for assignment {} to {}'.format(a, c.letter)
                )
            a.case = c
            a.save()
