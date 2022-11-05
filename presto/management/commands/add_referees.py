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
from django.contrib.auth.models import User
from django.conf import settings
from django.core.management.base import BaseCommand

from presto.models import Referee, EstafetteTemplate, EstafetteLeg, DEFAULT_DATE

# Add referees (specified by their usernames)
# for all legs of a relay template (specified by its name).
USER_NAMES = [
    'ebach',
    'melmalki',
]

TEMPLATE_NAME = 'Basic Policy Analysis (first 3 steps)'  # 'Modelleerestafette 2020 (4 stappen)'

class Command(BaseCommand):

    def handle(self, *args, **options):
        et = EstafetteTemplate.objects.get(name=TEMPLATE_NAME)
        l_set = EstafetteLeg.objects.filter(template=et)
        u_set = User.objects.filter(username__in=USER_NAMES)
        r_list = []
        for u in u_set:
            for l in l_set:
                r_list.append(Referee(user=u, estafette_leg=l))
        Referee.objects.bulk_create(r_list)
