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
from django.db.models import F

from presto.models import (Course, Item, EstafetteTemplate, EstafetteLeg, Estafette, EstafetteCase,
                           PeerReview, Appeal, DEFAULT_DATE)

from markdown import markdown

# convert grade_motivation, appraisal_comment, and improvement_appraisal_comment fields
# of ALL PeerReview records from markdown format to HTML
class Command(BaseCommand):

    def handle(self, *args, **options):
        q = Course.objects.exclude(description='').exclude(description__icontains='<p>')
        print(len(q), ' course descriptions')
        for obj in q:
            obj.description=markdown(obj.description)
            obj.save()
        print('Done.')
        q = Item.objects.exclude(instruction='').exclude(instruction__icontains='<p>')
        print(len(q), ' item instructions')
        for obj in q:
            obj.instruction=markdown(obj.instruction)
            obj.save()
        print('Done.')
        q = EstafetteTemplate.objects.exclude(description='').exclude(description__icontains='<p>')
        print(len(q), 'estafette templates')
        for obj in q:
            obj.description=markdown(obj.description)
            obj.default_rules=markdown(obj.default_rules)
            obj.save()
        print 'Done.'
        q = EstafetteLeg.objects.exclude(description='').exclude(description__icontains='<p>')
        print(len(q), ' estafette legs')
        for obj in q:
            obj.description=markdown(obj.description)
            obj.upload_instruction=markdown(obj.upload_instruction)
            obj.review_instruction=markdown(obj.review_instruction)
            obj.save()
        print 'Done.'
        q = Estafette.objects.exclude(description='').exclude(description__icontains='<p>')
        print(len(q), ' estafettes')
        for obj in q:
            obj.description=markdown(obj.description)
            obj.save()
        print 'Done.'
        q = EstafetteCase.objects.exclude(description='').exclude(description__icontains='<p>')
        print(len(q), ' case descriptions')
        for obj in q:
            obj.description=markdown(obj.description)
            obj.save()
        print 'Done.'
        q = PeerReview.objects.exclude(grade_motivation='').exclude(grade_motivation__icontains='<p>')
        print(len(q), ' peer reviews')
        for obj in q:
            obj.grade_motivation=markdown(obj.grade_motivation)
            obj.appraisal_comment=markdown(obj.appraisal_comment)
            obj.improvement_appraisal_comment=markdown(obj.improvement_appraisal_comment)
            obj.save()
        print 'Done.'
        q = Appeal.objects.exclude(grade_motivation='').exclude(grade_motivation__icontains='<p>')
        print(len(q), ' appeals')
        for obj in q:
            obj.grade_motivation=markdown(obj.grade_motivation)
            obj.predecessor_motivation=markdown(obj.predecessor_motivation)
            obj.successor_motivation=markdown(obj.successor_motivation)
            obj.save()
        print 'Done.'
