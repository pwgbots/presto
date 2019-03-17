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
from django.contrib.auth.models import User
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.html import strip_tags 

# python modules
from datetime import date, datetime, time, timedelta
from hashlib import md5
from json import dumps, loads
from langdetect import detect, detect_langs
import os
import random
import re

# presto models
from presto.uiphrases import UI_LANGUAGE_CODES, UI_PHRASE_DICT, UI_BLACKDICT
from presto.utils import (half_points, int_to_base36, log_message,
    plural_s, prefixed_user_name, word_count)

tz = timezone.get_current_timezone()
DEFAULT_DATE = tz.localize(datetime.strptime('2001-01-01 00:00', '%Y-%m-%d %H:%M'))
NO_SESSION_KEY = '(no key)'

CALENDAR_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday',
    'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September',
    'October', 'November', 'December']

MINIMUM_INSTRUCTOR_WORD_COUNT = 10

STAR_DIVIDER = '<h4 class="ui horizontal divider header">&#9734;&#9734;&#9734;&#9734;&#9734;</h4>'

class Language(models.Model):
    name = models.CharField(max_length=60)
    code = models.CharField(max_length=10)

    # returns the properties of this language in readable form
    def __unicode__(self):
        return self.name + ' (' + self.code + ')'

    # returns a zero-based index for this language (independent of its DB key)
    def nr(self):
        return UI_LANGUAGE_CODES.index(self.code)

    # returns the phrase with index key in this language,
    # or if no such translation exists, in English, or if that fails the key itself
    def phrase(self, key):
        p_tuple = UI_PHRASE_DICT.get(key, '')
        if not p_tuple:
            return key
        n = self.nr()
        if n < len(p_tuple):
            return p_tuple[n]
        else:
            return p_tuple[0]

    def translate_fdt(self, s):
        for name in CALENDAR_NAMES:
            s = s.replace(name, self.phrase(name))
        return s

    def fdate(self, d):
        # d = timezone.localtime(d)
        return ''.join([self.phrase(d.strftime('%A')),
            (',' if self.code == 'en-US' else ''), d.strftime(' %d '),
            self.phrase(d.strftime('%B')), d.strftime(' %Y')])

    def ftime(self, dt):
        return self.fdate(dt) + timezone.localtime(dt).strftime(' %H:%M')

    # returns a nice formulation of penalty points alotted by a referee
    # NOTE: negative values signify bonus points!
    def penalties_as_text(self, pp, sp):
        pp = float(pp)
        sp = float(sp)
        if abs(pp) < 0.25 and abs(sp) < 0.25:
            return self.phrase('No_sanctions')
        else:
            pl = []
            if pp >= 0.25:
                pl.append(self.phrase('Penalty_for_predecessor') % half_points(pp))
            elif pp <= -0.25:
                pl.append(self.phrase('Bonus_for_predecessor') % half_points(pp))
            if sp >= 0.25:
                pl.append(self.phrase('Penalty_for_successor') % half_points(sp))
            elif sp <= -0.25:
                pl.append(self.phrase('Bonus_for_successor') % half_points(sp))
            return self.phrase('Sanctions') + ', '.join(pl)


    # MH inspired by: http://david.feinzeig.com/blog/2013/05/12/behold-the-power-of-default-how-to-set-the-default-argument-of-a-django-model-field-equal-to-a-class-method-using-lambda/
    @classmethod
    def get_first_language(self):
        try:
            return Language.objects.first().id
        except:
            return None


# defines the 4 possible user roles and associates a Semantic UI icon with them
class Role(models.Model):
    name = models.CharField(max_length=16)
    rank = models.IntegerField()
    icon = models.CharField(max_length=32, default='')
    class Meta:
        ordering = ('rank', 'name')

    def __unicode__(self):
        return '%d - %s' % (self.rank, self.name)


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    # SSO NetID is assumed to be recorded in Django's user.username
    # full surf identity (e.g., pbots@tudelft.nl) has structure net_id@organization_id
    organization_id = models.CharField(max_length=64, blank=True)  # e.g., tudelft.nl
    is_employee = models.BooleanField(default=False)
    # if user is authenticated via edX, Django's username will be the edX identifier
    # and the user is prompted to enter his/her first and last name
    is_edx_user = models.BooleanField(default=False)
    registration_number = models.CharField(max_length=32, blank=True)  # ISIS$xxxxxxx is student number
    roles = models.ManyToManyField(Role)

    def __unicode__(self):
        return '%s (%s)' % (prefixed_user_name(self.user), self.user.username )

    def has_role(self, role_name):
        return self.roles.filter(role__name=role_name).count > 0


# ensure that profile instance is created each time a new user is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


# generates a string of 32 hexadecimal digits that can be used as encoder/decoder
def random_hex32():
    return format(random.getrandbits(128), 'x').zfill(32)

def pq_dir_name():
    return 'PQ_' + random_hex32()

def template_dir_name():
    return 'T_' + random_hex32()

def relay_dir_name():
    return 'R_' + random_hex32()

class UserSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=64, default=NO_SESSION_KEY)
    decoder = models.CharField(max_length=32, default=random_hex32)
    encoder = models.CharField(max_length=32, default=random_hex32)
    start_time = models.DateTimeField(default=timezone.now)
    last_action = models.DateTimeField(default=timezone.now)
    active_role = models.ForeignKey(Role, null=True, blank=True, on_delete=models.SET_NULL)
    # state is a dictionary (encoded as JSON string) that may hold state variables
    # presently used for tracking whether a demo alias is set for the user:
    # - course_student_id (int) then holds the primary key of the CourseStudent instance
    # - alias_name (string) then holds the name entered by the user when prompted for this alias
    state = models.TextField(default='{}', blank=True)

    def __unicode__(self):
        return '%s [%s] %s %s' % (prefixed_user_name(self.user),
            str(self.last_action).encode('utf-8').decode('utf-8')[:19],
            self.session_key, self.state)


class Course(models.Model):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True, default='')
    start_date = models.DateField(blank=True, default=DEFAULT_DATE)
    end_date = models.DateField(blank=True, default=DEFAULT_DATE)
    manager = models.ForeignKey(User, on_delete=models.PROTECT)
    instructors = models.ManyToManyField(User, related_name='course_instructor')
    # formal name (with academic titles) and position to sign letters of acknowledgement with
    staff_name = models.CharField(max_length=128, blank=True, default='')
    staff_position = models.CharField(max_length=128, blank=True, default='')
    language = models.ForeignKey(Language,
        default=Language.get_first_language(), on_delete=models.SET_DEFAULT)
    # badge color is encoded in lower 4 bytes: disc number (highest), red , green, blue (lowest)
    badge_color = models.IntegerField(default=0)
    is_edX = models.BooleanField(default=False)
    is_hidden = models.BooleanField(default=False)
    # every course has own subdirectory for pictures: upload/PQ_ plus 32 hex digits
    picture_dir = models.CharField(max_length=35, unique=True, default=pq_dir_name)
    picture_queue_open = models.BooleanField(default=False)
    picture_queue_strict = models.BooleanField(default=False)

    class Meta:
        ordering = ('code', 'name')

    def __unicode__(self):
        return '%s--%s' % (self.code, self.name)

    def title(self):
        return '<em>%s</em> (%s)' % (self.name, self.code)


class CourseStudent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    dummy_index = models.IntegerField(default=0)
    particulars = models.CharField(max_length=16, blank=True, default='')
    time_enrolled = models.DateTimeField(default=timezone.now)
    last_action = models.DateTimeField(default=timezone.now)
    # optional field for awards that are conditional on having passed the entire course
    has_passed = models.BooleanField(default=False)

    # NOTE: the dummy_index allows instructors to create "dummy participants"
    #       by enrolling one or more times in a course and joining associated estafettes
    class Meta:
        ordering = ('user', 'course', 'dummy_index')
        unique_together = ['user', 'course', 'dummy_index']

    def __unicode__(self):
        if self.dummy_index < 0:
            return '#%d-%s: Course instructor (%s)' % (self.id,
                self.course.code, prefixed_user_name(self.user))
        if self.dummy_index > 0:
            index = ' (%d)' % self.dummy_index
        else:
            index = ''
        return '#%d-%s: %s%s' % (self.id, self.course.code, prefixed_user_name(self.user), index)

    def dummy_name(self):
        if self.dummy_index > 0:
            index = ' (dummy # %d)' % self.dummy_index
        else:
            index = ''
        return '%s%s' % (prefixed_user_name(self.user), index)

    def pin(self):
        return str(int(md5(self.particulars.encode('ascii', 'ignore') + str(self.dummy_index)
            ).hexdigest()[4:11], 16))[:4].zfill(4)


# Items may be appraised on different scales, specified by a string according to this syntax:
#   rating:(range):(symbol)                  where (symbol) may be "star" or "heart"
#   likert:(range):(low label):(high label)  where labels express meaning of the scale ends
#   score:(range):(style)                    where (style) may be "input", "dropdown" or "menu"
#   icons:(icon 1|color):(icon 2|color): ... where (icon N) must be a valid Semantic UI icon name
#   options:(option 1):(option 2): ...       where (option N) must be a non-empty string
# NOTE: (range) denotes highest value (integer > 1); lower end of a range is by definition 1

class Item(models.Model):
    number = models.IntegerField(default=1)
    name = models.CharField(max_length=128)
    instruction = models.TextField(blank=True, default='')
    word_count = models.IntegerField(default=0)
    appraisal = models.CharField(max_length=128, blank=True, default='')
    no_comment = models.BooleanField(default=False)

    class Meta:
        ordering = ['number']

    def __unicode__(self):
        return '%d. %s' % (self.number, self.name)

    def as_html(self):
        return '<h4>%d. %s</h4>%s' % (self.number, self.name, self.instruction)

    # item definitions are part of templates and hence must be "copyable"
    def to_dict(self):
        fl = re.sub('<[^<]+?>', ' ', self.instruction)
        if len(fl) > 50:
            fl = fl[:50] + '&hellip;'
        return {
            'number': self.number,
            'name': self.name,
            'instruction': self.instruction,
            'first_line': fl,
            'word_count': self.word_count,
            'appraisal': self.appraisal
        }

    def init_from_dict(self, d):
        self.number = d['number']
        self.name = d['name']
        self.instruction = d.get('instruction', '')
        self.word_count = d.get('word_count', 0)
        self.appraisal = d.get('appraisal', '')


class QuestionnaireTemplate(models.Model):
    name = models.CharField(max_length=128, unique=True)
    description = models.TextField(blank=True, default='')
    items = models.ManyToManyField(Item)
    creator = models.ForeignKey(User, related_name='evt_creator', on_delete=models.PROTECT)
    editors = models.ManyToManyField(User, related_name='evt_editors', blank=True)
    last_editor = models.ForeignKey(User, related_name='evt_last_editor', null=True,
        on_delete=models.SET_NULL)
    time_created = models.DateTimeField(default=timezone.now)
    time_last_edit = models.DateTimeField(default=timezone.now)
    published = models.BooleanField(default=False)

    def __unicode__(self):
        return 'QT: %s' % self.name


class EstafetteTemplate(models.Model):
    name = models.CharField(max_length=128, unique=True)
    description = models.TextField(blank=True, default='')
    default_rules = models.TextField(blank=True, default='')
    # every template has own subdirectory (T_ plus 32 hex digits) in the uploads directory
    upload_dir = models.CharField(max_length=34, unique=True, default=template_dir_name)
    creator = models.ForeignKey(User, related_name='est_creator', on_delete=models.PROTECT)
    editors = models.ManyToManyField(User, related_name='est_editors', blank=True)
    last_editor = models.ForeignKey(User, related_name='est_last_editor', null=True,
        on_delete=models.SET_NULL)
    time_created = models.DateTimeField(default=timezone.now)
    time_last_edit = models.DateTimeField(default=timezone.now)
    published = models.BooleanField(default=False)

    def __unicode__(self):
        return 'ET: %s' % self.name

    def nr_of_legs(self):
        return EstafetteLeg.objects.filter(template=self).count()

    # returns relevant fields as JSON string to facilitate duplication and/or publication for reuse
    # NOTE: creator, last_editor and time stamp fields are ignored, because these
    #       are set upon creation of the duplicating instance
    def to_JSON(self):
        legs = EstafetteLeg.objects.filter(template=self)
        d = {
            'name': self.name,
            'description': self.description,
            'default_rules': self.default_rules,
            'legs': [l.to_dict() for l in legs]
            }
        return dumps(d)

    # set not-author-related fields to corresponding values specified by JSON string
    def init_from_JSON(self, json_str, user):
        d = loads(json_str)
        # ensure that name is unique in database
        names = EstafetteTemplate.objects.values_list('name', flat=True)
        n = 0
        nn = d['name']
        while nn in names:
            n += 1
            nn = d['name'] + ' (%d)' % n
        # now the original name is suffixed by (n) with n the smallest unused integer
        self.name = nn
        self.description = d['description']
        self.default_rules = d['default_rules']
        self.creator = user
        self.last_editor = user
        # store the new object in the database, or its primary key will not be known yet
        self.save()
        # now the legs can be created
        for l in d['legs']:
            leg = EstafetteLeg()
            leg.template = self
            # NOTE: l is a dict and hence must be serialized again
            leg.init_from_dict(l, user)
        log_message('Initialized template %s from JSON string' % self.name, user)


# assumes that string is a semi-colon separated string
# with substrings "prompt:name.ext1,ext2, ..." and returns a list of dictionaries
# with entries "prompt", "name", and "types" for use in HTML5 file upload form
def string_to_file_list(s):
    fl = []
    # empty string => empty file list
    # NOTE: this is functional only if the assignment as items
    if s == '':
        return fl 
    try:
        n = 1
        rf = s.replace(', ', ';')
        for f in rf.split(';'):
            pr = f.strip().split(':')
            if len(pr) == 1:
                pr = ['File', pr[0]]
            nx = pr[1].split('.')
            if len(nx) == 1:
                nx = ['file%d' % n, nx[0]]
                n += 1
            fl.append({'prompt': pr[0],
                       'name': nx[0],
                       'types': '.' + ',.'.join(nx[1].split(','))})
    except Exception, e:
        fl = [{'prompt':'ERROR', 'name': str(e), 'types': rf}]
    return fl


class EstafetteLeg(models.Model):
    template = models.ForeignKey(EstafetteTemplate, on_delete=models.CASCADE)
    number = models.IntegerField(default=1)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True, default='')
    learning_objectives = models.TextField(blank=True, default='')
    upload_instruction = models.TextField()
    upload_items = models.ManyToManyField(Item, related_name='assignment_item')
    review_instruction = models.TextField()
    review_items = models.ManyToManyField(Item)
    # developer may specify a model text (template) for a review
    review_model_text = models.TextField(blank=True, default='')
    word_count = models.IntegerField(default=50)
    # minimum time (in minutes) before participant can submit review / upload work
    min_review_minutes = models.IntegerField(default=30)
    min_upload_minutes = models.IntegerField(default=120)
    required_files = models.CharField(max_length=256, blank=True, default='')
    rejectable = models.BooleanField(default=False)
    # optionally, instructors may require a specific title and length (word count)
    # for the report section that is to be added in this step,
    # so that the software can check this when the participant uploads work
    required_section_title = models.CharField(max_length=256, blank=True)
    required_section_length = models.IntegerField(default=0)
    required_keywords = models.CharField(max_length=512, blank=True)
    # keep track who first added this step, and who last edited it
    creator = models.ForeignKey(User, related_name='el_creator', on_delete=models.PROTECT)
    last_editor = models.ForeignKey(User, related_name='el_editor', null=True, on_delete=models.SET_NULL)
    time_created = models.DateTimeField(default=timezone.now)
    time_last_edit = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ('template', 'number')
        unique_together = ['template', 'number']

    def __unicode__(self):
        return 'EL#%d: %s (#%d in %s)' % (self.id, self.name, self.number, self.template.name)

    def file_list(self):
        return string_to_file_list(self.required_files)

    # returns review instruction plus all review item instructions as one HTML string
    def complete_review_instruction(self):
        cri = (''.join([ri.as_html() for ri in self.review_items.all()])
            + STAR_DIVIDER + self.review_instruction)
        # check whether HTML contains more than just empty paragraphs (as generated by Quill)
        if cri.replace('<p><br></p>', ''):
            return cri
        # if not, return an empty string
        return ''

    # returns relevant fields as a dict to facilitate template duplication and/or publication for reuse
    # NOTE: creator, last_editor and time stamp fields are ignored, because these
    #       are set upon creation of the duplicating instance
    def to_dict(self):
        return {
            'number': self.number,
            'name': self.name,
            'description': self.description,
            'learning_objectives': self.learning_objectives,
            'upload_instruction': self.upload_instruction,
            'review_instruction': self.review_instruction,
            'review_model_text': self.review_model_text,
            'word_count': self.word_count,
            'min_review_minutes': self.min_review_minutes,
            'min_upload_minutes': self.min_upload_minutes,
            'required_files': self.required_files,
            'self.rejectable': self.rejectable,
            'required_section_title': self.required_section_title,
            'required_section_length': self.required_section_length,
            'required_keywords': self.required_keywords,
            'upload_items': [i.to_dict() for i in self.upload_items.all()],
            'review_items': [i.to_dict() for i in self.review_items.all()],
            'creator': prefixed_user_name(self.creator),
            'last_editor': prefixed_user_name(self.last_editor),
            'time_created': timezone.localtime(self.time_created).strftime('%Y-%m-%d %H:%M'),
            'time_last_edit': timezone.localtime(self.time_last_edit).strftime('%Y-%m-%d %H:%M'),
            }

    # set not-author-related fields to corresponding values in dictionary d
    def init_from_dict(self, d, user):
        self.number = d['number']
        self.name = d['name']
        self.description = d.get('description', '')
        self.learning_objectives = d.get('learning_objectives', '')
        self.upload_instruction = d.get('upload_instruction', '')
        self.review_instruction = d.get('review_instruction', '')
        self.review_model_text = d.get('review_model_text', '')
        self.word_count = d.get('word_count', 0)
        self.min_review_minutes = d.get('min_review_minutes', 0)
        self.min_upload_minutes = d.get('min_upload_minutes', 0)
        self.required_files = d.get('required_files', '')
        self.rejectable = d.get('self.rejectable', False)
        self.required_section_title = d.get('required_section_title', '')
        self.required_section_length = d.get('required_section_length', '')
        self.required_keywords = d.get('required_keywords', '')
        for i in d['upload_items']:
            ui = Item()
            ui.init_from_dict(i)
        for i in d['review_items']:
            ri = Item()
            ri.init_from_dict(i)
        self.creator = user
        self.last_editor = user
        self.save()


class Estafette(models.Model):
    template = models.ForeignKey(EstafetteTemplate, on_delete=models.PROTECT)
    name = models.CharField(max_length=128, unique=True)
    description = models.TextField(blank=True, default='')
    # every relay has own subdirectory (R_ plus 32 hex digits) in the uploads directory
    upload_dir = models.CharField(max_length=34, unique=True, default=relay_dir_name)
    # will be combined with course color to obtain badge color for a course estafette
    badge_shade = models.IntegerField(default=0)
    # time needed (on average) to referee an appeal case (in hours)
    hours_per_appeal = models.FloatField(default=1)
    creator = models.ForeignKey(User, related_name='e_creator', on_delete=models.PROTECT)
    editors = models.ManyToManyField(User, related_name='e_editors', blank=True)
    last_editor = models.ForeignKey(User, related_name='e_last_editor', null=True,
        on_delete=models.SET_NULL)
    time_created = models.DateTimeField(default=timezone.now)
    time_last_edit = models.DateTimeField(default=timezone.now)
    published = models.BooleanField(default=False)

    def __unicode__(self):
        return '%s (T: %s)' % (self.name, self.template.name)

    # returns the number of cases defined for this relay
    def nr_of_cases(self):
        return EstafetteCase.objects.filter(estafette=self).count()


# returns the path to the relay directory for the specified CaseUpload instance
def case_dir(instance, filename):
    return os.path.join(instance.estafette.upload_dir, filename)


class CaseUpload(models.Model):
    estafette = models.ForeignKey(Estafette, on_delete=models.CASCADE)
    upload_file = models.FileField(upload_to=case_dir)
    original_name = models.CharField(max_length=256)
    time_uploaded = models.DateTimeField(default=timezone.now)

    def __unicode__(self):
        return '#%d-%s (%s)' % (self.id, self.original_name, unicode(self.estafette))


class EstafetteCase(models.Model):
    estafette = models.ForeignKey(Estafette, on_delete=models.PROTECT)
    letter = models.CharField(max_length=1)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True, default='')
    required_keywords = models.CharField(max_length=512, blank=True)
    upload = models.ForeignKey(CaseUpload, null=True, blank=True, on_delete=models.SET_NULL)
    creator = models.ForeignKey(User, related_name='ec_creator', on_delete=models.PROTECT)
    last_editor = models.ForeignKey(User, related_name='ec_editor',
        null=True, blank=True, on_delete=models.SET_NULL)
    time_created = models.DateTimeField(default=timezone.now)
    time_last_edit = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ('estafette', 'letter')
        unique_together = ['estafette', 'letter']

    def __unicode__(self):
        return 'EC: %s (%s) %s' % (self.name, self.letter, self.estafette.name)


class CourseEstafette(models.Model):
    course = models.ForeignKey(Course, on_delete=models.PROTECT)
    estafette = models.ForeignKey(Estafette, on_delete=models.PROTECT)
    suffix = models.CharField(max_length=8, default='', blank=True)
    start_time = models.DateTimeField(default=DEFAULT_DATE)
    deadline = models.DateTimeField(default=DEFAULT_DATE)
    review_deadline = models.DateTimeField(default=DEFAULT_DATE)
    end_time = models.DateTimeField(default=DEFAULT_DATE)
    actual_rules = models.TextField(blank=True, default='')
    questionnaire_template = models.ForeignKey(QuestionnaireTemplate,
        null=True, blank=True, on_delete=models.SET_NULL)
    final_reviews = models.IntegerField(default=0)
    with_review_clips = models.BooleanField(default=False)
    with_badges = models.BooleanField(default=False)
    with_referees = models.BooleanField(default=False)
    # scoring system 0 = relative differential; 1 = absolute with differential bonus
    scoring_system = models.IntegerField(default=0)
    low_score_range = models.FloatField(default=-1000)
    high_score_range = models.FloatField(default=1000)
    low_grade_range = models.FloatField(default=1)
    high_grade_range = models.FloatField(default=10)
    passing_grade = models.FloatField(default=5.5)
    speed_bonus = models.FloatField(default=0)
    bonus_per_step = models.BooleanField(default=False)
    is_hidden = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        unique_together = ['course', 'estafette', 'suffix']
        ordering = ('end_time', 'start_time')

    def __unicode__(self):
        return '#%d-%s--%s%s%s' % (self.id, self.course.code,
            self.estafette.name,' (%s)' % self.suffix if self.suffix else '',
            '--DELETED' if self.is_deleted else '')

    def title(self):
        return '%s <em>%s</em>%s' % (self.course.code,
            self.estafette.name, (' (%s)' % self.suffix if self.suffix else ''))
    
    # returns a 3-tuple (next deadline, phrase for this deadline, color name)
    # where next deadline is a datetime object, the phrase an entry in the language dict,
    # while color name denotes a Semantic UI color that reflects how pressing the deadline is 
    def next_deadline(self):
        now = timezone.now()
        if self.deadline > now:
            next_dl = self.deadline
            dl_phrase = 'Deadline_for_assignments'
            num = (next_dl - now).total_seconds()
            den = (next_dl - self.start_time).total_seconds()
        elif self.review_deadline > now:
            next_dl = self.review_deadline
            dl_phrase = 'Deadline_for_reviews'
            num = (next_dl - now).total_seconds()
            den = (next_dl - self.deadline).total_seconds()
        else:
            next_dl = self.end_time
            if next_dl > now:
                dl_phrase = 'Deadline_for_responses'
                num = (next_dl - now).total_seconds()
                den = (next_dl - self.review_deadline).total_seconds()
            else:
                dl_phrase = 'Relay_is_closed'
                num = 0
        if num <= 0 or den <= 0:
            perc = 0
        else:
            perc = num / den
        if perc > 0.5:
            color = 'green '
        elif perc > 0.3:
            color = 'olive'
        elif perc > 0.2:
            color = 'yellow'
        elif perc > 0.1:
            color = 'orange'
        else:
            color = 'red'
        lang = self.course.language
        return {'time': lang.ftime(next_dl), 'label': lang.phrase(dl_phrase), 'color': color}

    # returns a list of leg numbers for this estafette in ascending order (= default ordering)
    def leg_numbers(self):
        return EstafetteLeg.objects.filter(template=self.estafette.template
            ).value_list('number', flat=True)

    # returns a (most likely!) unique five-digit base36 code for this estafette
    def demonstration_code(self):
        # only the DEMO course has a demonstration course
        if self.course.code != 'DEMO':
            return ''
        # get a *deterministic* 33-digit hash with a leading non-zero digit
        hx = md5(unicode(self).encode('ascii', 'ignore')).hexdigest()
        return int_to_base36(int('7' + hx, 16))[1:6]
        # NOTE: 1:6 is an arbitrary selection; with the added leading 7, the 32+1 hex digits
        #       will give at least 25 base36 digits
        #       cf. http://www.unitconversion.org/numbers/base-16-to-base-36-conversion.html

    # returns a tuple (LTI consumer ID, secret) for this course if it is an edX course
    # NOTE: the LTI consumer ID is a (most likely!) unique 8-digit base36 string, while
    #       the secret is a 16-digit base36 string
    def LTI_consumer_secret(self):
        # no consumer_secret for non-edX courses
        if not self.course.is_edX:
            return None
        # get a *deterministic* 32-digit hash
        hx = md5(unicode(self).encode('ascii', 'ignore') * 3).hexdigest()
        b36 = int_to_base36(int('b' + hx, 16))
        return (b36[1:9], b36[9:25])


class Participant(models.Model):
    student = models.ForeignKey(CourseStudent, on_delete=models.PROTECT)
    estafette = models.ForeignKey(CourseEstafette, on_delete=models.PROTECT)
    # every participant has own subdirectory (32 hex digits) in the uploads directory
    upload_dir = models.CharField(max_length=32, unique=True, default=random_hex32)
    time_registered = models.DateTimeField(default=timezone.now)
    time_last_action = models.DateTimeField(default=timezone.now)
    time_started = models.DateTimeField(default=DEFAULT_DATE)
    final_grade = models.FloatField(default=-1)
    deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ('estafette', 'student')
        unique_together = ['student', 'estafette']

    def submitted_steps(self):
        return Assignment.objects.filter(participant=self).exclude(time_uploaded=DEFAULT_DATE
            ).filter(clone_of__isnull=True).count()

    def __unicode__(self):
        return '#%d-%s-%s%s' % (self.id, unicode(self.student), unicode(self.estafette),
                                '--DELETED' if self.deleted else '')

    def shorthand(self):
        return '%s' % unicode(self.student)

    def progress(self):
        return (Assignment.objects.filter(participant=self).count()
            + PeerReview.objects.filter(reviewer=self).count())

    # returns a dict with progress data for each step and final review (for display as progress bar)
    def things_to_do(self):
        lang = self.student.course.language
        steps = self.estafette.estafette.template.nr_of_legs()
        all_steps_done = False
        all_final_reviews_done = self.estafette.final_reviews == 0
        last_completed = DEFAULT_DATE
        # initialize "to do" list to contain a dict for each step
        ttd = [{
            'step': i + 1,
            'assigned': False,
            'assigned_tip': lang.phrase('Step_not_assigned') % (i + 1),
            'downloaded': False,
            'downloaded_tip': lang.phrase('Step_not_downloaded') % i,
            'reviewed': False,
            'reviewed_tip': lang.phrase('Step_not_reviewed') % i,
            'uploaded': False,
            'uploaded_tip': lang.phrase('Step_not_uploaded') % (i + 1),
            } for i in range(steps)]
        # add data for each assignment this participant has worked on so far (ignoring clones)
        for a in Assignment.objects.filter(participant=self, clone_of__isnull=True):
            t = ttd[a.leg.number - 1]
            t['assigned'] = True
            t['assigned_tip'] = lang.phrase('Step_assigned') % (t['step'],
                lang.ftime(a.time_assigned))
            if a.leg.number > 1:
                # NOTE: show tooltip only if step has required files
                if a.leg.required_files:
                    # check whether the student already downloaded the predecessor's work
                    dl = UserDownload.objects.filter(user=self.student.user,
                        assignment=a.predecessor)
                    if dl:
                        t['downloaded'] = True
                        t['downloaded_tip'] = lang.phrase('Step_downloaded'
                            ) % (t['step'] - 1, lang.ftime(dl.first().time_downloaded))
                else:
                    t['downloaded'] = True
                    t['downloaded_tip'] = t['assigned_tip']
                ur = PeerReview.objects.filter(assignment=a.predecessor, reviewer=self)
                if ur:
                    ur = ur.first()
                    if ur.time_submitted != DEFAULT_DATE:
                        t['reviewed'] = True
                        t['reviewed_tip'] = lang.phrase('Step_reviewed'
                            ) % (t['step'] - 1, lang.ftime(ur.time_submitted))
            if a.time_uploaded != DEFAULT_DATE:
                t['uploaded'] = True
                t['uploaded_tip'] = lang.phrase('Step_uploaded'
                    ) % (t['step'], lang.ftime(a.time_uploaded))
                last_completed = a.time_uploaded
                all_steps_done = t['step'] == steps
        # add dicts for final reviews
        ttd += [{
            'review': i + 1,
            'downloaded': False,
            'downloaded_tip': lang.phrase('Review_not_downloaded') % (i + 1),
            'reviewed': False,
            'reviewed_tip': lang.phrase('Review_not_uploaded') % (i + 1)
            } for i in range(self.estafette.final_reviews)]
        # add data for each final review this participant has worked on so far
        for ur in PeerReview.objects.filter(reviewer=self, final_review_index__gt=0):
            t = ttd[steps + ur.final_review_index - 1]
            if ur.time_first_download != DEFAULT_DATE:
                t['downloaded'] = True
                t['downloaded_tip'] = lang.phrase('Review_downloaded'
                    ) % (t['review'], lang.ftime(ur.time_first_download))
            if ur.time_submitted != DEFAULT_DATE:
                t['reviewed'] = True
                t['reviewed_tip'] = lang.phrase('Review_reviewed'
                    ) % (t['review'], lang.ftime(ur.time_submitted))
                last_completed = ur.time_submitted
                all_final_reviews_done = t['review'] == self.estafette.final_reviews
        if all_steps_done and all_final_reviews_done:
            ttd += [{'finish': lang.ftime(last_completed)}]
        return ttd


class Assignment(models.Model):
    participant = models.ForeignKey(Participant, on_delete=models.PROTECT)
    case = models.ForeignKey(EstafetteCase, on_delete=models.PROTECT)
    leg = models.ForeignKey(EstafetteLeg, on_delete=models.PROTECT)
    # is_selfie indicates whether this is a clone made for the participant
    # so that s/he can continue with his/her own work
    is_selfie = models.BooleanField(default=False)
    time_assigned = models.DateTimeField(default=timezone.now)
    time_uploaded = models.DateTimeField(default=DEFAULT_DATE)
    predecessor = models.ForeignKey('self', related_name='preceding_assignment',
        null=True, blank=True, on_delete=models.SET_NULL)
    successor = models.ForeignKey('self', related_name='succeeding_assignment',
        null=True, blank=True, on_delete=models.SET_NULL)
    clone_of = models.ForeignKey('self', related_name='original_assignment',
        null=True, blank=True, on_delete=models.PROTECT)
    time_scanned = models.DateTimeField(default=DEFAULT_DATE)
    scan_result = models.IntegerField(default=0)
    time_first_download = models.DateTimeField(default=DEFAULT_DATE)
    time_last_download = models.DateTimeField(default=DEFAULT_DATE)
    # set this flag when the participant rejects this assignment
    # NOTE: this means that s/he rejects THIS assignment because it requires building
    #       on a (bad!) predecessor assignment; this assignment must remain in the database
    #       to keep the participant history complete
    is_rejected = models.BooleanField(default=False)

    # NOTE: each participant can have only one assignment per leg, but this work may be cloned
    class Meta:
        unique_together = ['participant', 'leg', 'clone_of']

    def __unicode__(self):
        if self.time_uploaded == DEFAULT_DATE:
            suffix = ''
        else:
            suffix = ' (%s)' % timezone.localtime(self.time_uploaded).strftime('%Y-%m-%d %H:%M')
            if self.clone_of != None:
                if self.is_selfie:
                    suffix += ' SELFIE'
                else:
                    suffix += ' CLONE'
            if self.is_rejected:
                suffix += ' [REJ]'
            if self.successor != None:
                suffix += ' => ' + self.successor.participant.shorthand()
        return '#%d-%d%s-%s%s'% (self.pk, self.leg.number, self.case.letter, unicode(self.participant), suffix)

    # returns the bonus deadline as a course-language-formatted date-time string if this assignment
    # was submitted before its bonus_per_step deadline, or if it still can be sumbitted on time
    # (taking into account the enforced waiting time); otherwise returns an empty string 
    def on_time_for_bonus(self, min_to_wait = 0):
        # get the course relay
        r = self.participant.estafette
        if r.bonus_per_step:
            # if the assignment has been sumbitted, check the time it was uploaded
            if self.time_uploaded != DEFAULT_DATE:
                t = self.time_uploaded
            else:
                t = timezone.now()
            # (1) calculate time between assigned and assignments deadline MINUS 24 hours
            no_bonus_delta = timedelta(days=1)
            
            # NOTE: As of 01-01-2019, the speed bonus term is T - MAX(T/4, 24h), i.e.,
            #       the time available for assignments minus either 25% of the time, or 1 full day.
            if r.start_time < tz.localize(datetime.strptime('2019-01-01', '%Y-%m-%d')):
                no_bonus_hours = round((r.deadline - r.start_time).total_seconds() / 3600 / 4)
                if no_bonus_hours > 24:
                    no_bonus_delta = timedelta(hours=no_bonus_hours)

            remaining_time = r.deadline - no_bonus_delta - self.time_assigned 
            # (2) calculate nominal time as remaining time / remaining steps
            nominal_time = remaining_time / (r.estafette.template.nr_of_legs() - self.leg.number + 1)
            # (3) calculate bonus deadline
            bd = self.time_assigned + nominal_time
            # (4) round it DOWN to quarter hour precision
            bd = timezone.make_aware(datetime(
                bd.year, bd.month, bd.day, bd.hour, 15 * (bd.minute // 15)))
            # (5) allow for 1 grace minute
            min_left = (bd - t).total_seconds() // 60 + 1
            # return FALSE if bonus is/was unattainable
            # NOTE: both conditions must be checked because min_to_wait may be less than zero
            if min_left > 0 and min_left > min_to_wait:
                return r.course.language.ftime(bd)
            else:
                return ''

    # returns list of items for this assignment, where each item is a dict
    # with properties relevant for I/O
    def item_list(self):
        # get the "upload item" list as defined for the related estafette leg
        lang = self.participant.student.course.language
        il = [{
            'item': i,
            'comment': '',
            'cmnt_words': 0,
            'rating': 0,
            'min_words': i.word_count
            } for i in self.leg.upload_items.all()]
        # add data for the items that have been filled in by the user
        for ia in ItemAssignment.objects.filter(assignment=self):
            il[ia.item.number - 1].update({
                'comment': ia.comment,
                'cmnt_words': word_count(ia.comment),
                'rating': ia.rating
                })
        return il

    # returns True iff all items have been rated (if needed) and count sufficient words
    def is_complete(self):
        ia_set = ItemAssignment.objects.filter(assignment=self)
        for i in self.leg.upload_items.all():
            try:
                ia = ia_set.get(item=i)
                # item saved? then check whether it is complete
                if (i.appraisal != '' and ia.rating == 0) or word_count(ia.comment) < i.word_count:
                    return False
            except:
                # item not even saved yet
                return False
        # nothing missing? then this assignment is complete
        return True


class ItemAssignment(models.Model):
    # item assignments relate to a specific upload item of an asssignment
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.PROTECT)
    comment = models.TextField(blank=True, default='')
    rating = models.IntegerField(blank=True, default=0)


# returns the path to the participant directory for the specified ParticipantUpload instance
def participant_dir(instance, filename):
    return os.path.join(instance.assignment.participant.upload_dir, filename)


class ParticipantUpload(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    file_name = models.CharField(max_length=32)
    upload_file = models.FileField(upload_to=participant_dir)
    time_uploaded = models.DateTimeField(default=timezone.now)

    def __unicode__(self):
        return '%s-%s: %s (%s)' % (unicode(self.assignment), self.file_name,
            self.upload_file.name, timezone.localtime(self.time_uploaded).strftime('%Y-%m-%d %H:%M'))


# Each download of an uploaded file (of zipped set) is registered.
# This allows checking per user whether s/he has indeed "seen" a file
class UserDownload(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    time_downloaded = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['time_downloaded']

    def __unicode__(self):
        return '%s: %s downloaded %s' % (timezone.localtime(self.time_downloaded).strftime('%Y-%m-%d %H:%M'),
            prefixed_user_name(self.user), unicode(self.assignment))


class PeerReview(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.PROTECT)
    reviewer = models.ForeignKey(Participant, on_delete=models.PROTECT)
    grade = models.IntegerField(default=0)
    is_second_opinion = models.BooleanField(default=False)
    final_review_index = models.IntegerField(default=0)
    is_rejection = models.BooleanField(default=False)
    # reviewer sets this flag when predecessor handed on work without adding own assignment
    step_not_performed = models.BooleanField(default=False)
    time_first_download = models.DateTimeField(default=DEFAULT_DATE)
    time_submitted = models.DateTimeField(default=DEFAULT_DATE)
    grade_motivation = models.TextField(default='', blank=True)
    appraisal = models.IntegerField(default=0)
    appraisal_comment = models.TextField(default='', blank=True)
    improvement_appraisal = models.IntegerField(default=0)
    improvement_appraisal_comment = models.TextField(default='', blank=True)
    time_appraised = models.DateTimeField(default=DEFAULT_DATE)
    # allow appraiser to raise a "red flag" in case of inappropriate language
    is_offensive = models.BooleanField(default=False)
    is_appeal = models.BooleanField(default=False)
    time_acknowledged = models.DateTimeField(default=DEFAULT_DATE)
    time_appeal_assigned = models.DateTimeField(default=DEFAULT_DATE)

    def __unicode__(self):
        if self.time_submitted == DEFAULT_DATE:
            ts = ''
        else:
            ts = ' (%s)' % timezone.localtime(self.time_submitted).strftime('%Y-%m-%d %H:%M')
        if self.grade < 1:
            gr = '?'
        else:
            gr = str(self.grade)
        if self.is_rejection:
            gr += ' [REJECT]'
        elif self.final_review_index:
            gr += ' [FINAL-%d]' % self.final_review_index
        if self.time_appraised == DEFAULT_DATE:
            ta = ''
        else:
            ta = ' (%s)' % timezone.localtime(self.time_appraised).strftime('%Y-%m-%d %H:%M')
        if self.appraisal < 1:
            ap = '-?'
        else:
            ap = '-%d' % self.appraisal
        if self.is_appeal:
            ap += ' [APPEAL]'
        return '#%d-%s --> #%d: %s%s - %s%s%s%s' % (self.id, unicode(self.reviewer),
            self.assignment.participant.id,
            self.assignment.case.letter, self.assignment.leg.number, gr, ts, ap, ta)

    # returns list of items for this review, where each item is a dict
    # with properties relevant for I/O
    def item_list(self):
        # get the item list as defined for the related estafette leg
        lang = self.assignment.participant.student.course.language
        instr_rev = self.reviewer.student.dummy_index < 0
        il = [{
            'item': i,
            'comment': '',
            'cmnt_words': 0,
            'rating': 0,
            'min_words': min(MINIMUM_INSTRUCTOR_WORD_COUNT, i.word_count) if instr_rev else i.word_count
            } for i in self.assignment.leg.review_items.all()]
        # add data for the items that have been filled in by the user
        for ir in ItemReview.objects.filter(review=self):
            il[ir.item.number - 1].update({
                'comment': ir.comment,
                'cmnt_words': word_count(ir.comment),
                'rating': ir.rating
                })
        return il

    # returns True iff all items and grade have been rated and sufficiently motivated
    def is_complete(self):
        # first check the overall review
        min_w = self.assignment.leg.word_count
        # NOTE: instructors are allowed to provide much briefer motivations
        instr_rev = self.reviewer.student.dummy_index < 0
        if instr_rev:
            min_w = min(min_w, MINIMUM_INSTRUCTOR_WORD_COUNT)
        if self.grade == 0 or word_count(self.grade_motivation) < min_w:
            return False
        # then the review items
        ir_set = ItemReview.objects.filter(review=self)
        for i in self.assignment.leg.review_items.all():
            try:
                ir = ir_set.get(item=i)
                min_w = i.word_count
                if instr_rev:
                    min_w = min(min_w, MINIMUM_INSTRUCTOR_WORD_COUNT)
                # item saved? then check whether it is complete
                if (i.appraisal != '' and ir.rating == 0) or word_count(ir.comment) < min_w:
                    return False
            except:
                # item not even saved yet
                return False
        # nothing missing? then this review is complete
        return True

    # checks all review (item) and response comments for blacklisted words
    # sets the flag and returns matched words if matches, or returns FALSE if none
    def check_offensiveness(self):
        text = ' '.join([ir.comment for ir in ItemReview.objects.filter(review=self)])
        text = ' '.join([text, self.grade_motivation,
            self.appraisal_comment, self.improvement_appraisal_comment])
        text = strip_tags(text.lower().replace('.', ' ').replace(',', ' ').replace(';', ' '
            ).replace('!', ' ').replace('?', ' '))
        # get the course estafette language
        lang = self.reviewer.student.course.language
        # check whether the text appears to be in that language
        # if probability too low, return detect_langs dict as string
        try:
            dlc = detect(text)
            if dlc != lang.code.split('-')[0]:
                raise ValueError('Detected %s while expecting %s' % (dlc, lang.code))
        except Exception, e:
            self.is_offensive = True
            self.save()
            return '%s -- %s' % (str(e), self)
        # else the language is OK, and we must scan for blacklisted words
        blacklist = UI_BLACKDICT[lang.code]
        matches = []
        for word in blacklist:
            if word in text:
                matches.append(word)
        if matches:
            self.is_offensive = True
            self.save()
            return '%s -- %s' % (self, ', '.join(matches))
        # unset flag is not offensive after new scan
        if self.is_offensive:
            self.is_offensive = False
            self.save()
        return False


class ItemReview(models.Model):
    # item reviews relate to a specific peer review item
    review = models.ForeignKey(PeerReview, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.PROTECT)
    comment = models.TextField(blank=True, default='')
    rating = models.IntegerField(blank=True, default=0)

    def __unicode__(self):
        return '#%d-%s' % (self.id, unicode(self.review))


# returns the path to the template directory for the specified RefereeExam instance
def template_dir(instance, filename):
    return os.path.join(instance.estafette_leg.template.upload_dir, filename)


class RefereeExam(models.Model):
    # exam pertains to one specific step in an estafette
    estafette_leg = models.ForeignKey(EstafetteLeg, on_delete=models.CASCADE)
    case_description = models.TextField(blank=True, default='')
    upload_file = models.FileField(upload_to=template_dir)
    uploader = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    time_uploaded = models.DateTimeField(default=timezone.now)
    review_text = models.TextField(blank=True, default='')
    review_grade = models.IntegerField(default=0)
    appeal_text = models.TextField(blank=True, default='')
    # answers for the 10 questions are stored as a 10-digit string
    best_answers = models.CharField(max_length=10)
    last_editor = models.ForeignKey(User, related_name='rx_editor',
        null=True, blank=True, on_delete=models.SET_NULL)

    def __unicode__(self):
        return '#%d-Exam: %s' % (self.id, unicode(self.estafette_leg))


class Referee(models.Model):
    # users qualify themselves, hence not CourseStudent or Participant
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # qualification pertains to one specific step in an estafette
    estafette_leg = models.ForeignKey(EstafetteLeg, on_delete=models.CASCADE)
    # NOTE: passed exam may be NULL for instructors
    passed_exam = models.ForeignKey(RefereeExam, null=True, blank=True, on_delete=models.PROTECT)
    time_qualified = models.DateTimeField(default=timezone.now)

    def __unicode__(self):
        return '%s - %s' % (prefixed_user_name(self.user), unicode(self.estafette_leg))


class Appeal(models.Model):
    # appeals link a referee to a review
    referee = models.ForeignKey(Referee, on_delete=models.PROTECT)
    review = models.ForeignKey(PeerReview, on_delete=models.PROTECT)
    # appeal_type is one of a set of options (to be defined)
    appeal_type = models.IntegerField(blank=True, default=0)
    time_first_viewed = models.DateTimeField(default=DEFAULT_DATE)
    time_decided = models.DateTimeField(default=DEFAULT_DATE)
    # referees must specify the grade that in their opninion is fair
    grade = models.IntegerField(default=0)
    # referees must motivate their decision
    grade_motivation = models.TextField(default='', blank=True)
    # referee may give penalties -- negative scores are in fact BONUS points!
    predecessor_penalty = models.FloatField(default=0)
    successor_penalty = models.FloatField(default=0)
    # parties must acknowledge viewing the verdict within 48 hours after the decision
    time_viewed_by_predecessor = models.DateTimeField(default=DEFAULT_DATE)
    time_viewed_by_successor = models.DateTimeField(default=DEFAULT_DATE)
    # then they have 24 hours to respond (incl. making a formal objection)
    time_acknowledged_by_predecessor = models.DateTimeField(default=DEFAULT_DATE)
    time_acknowledged_by_successor = models.DateTimeField(default=DEFAULT_DATE)
    # both parties must appraise the verdict (on a smiley scale)
    # NOTE: this appraisal may affect the referee's reputation score
    predecessor_appraisal = models.IntegerField(default=0)
    successor_appraisal = models.IntegerField(default=0)
    # appraisals must also be motivated
    predecessor_motivation = models.TextField(default='', blank=True)
    successor_motivation = models.TextField(default='', blank=True)
    # both parties may raise an objection
    is_contested_by_predecessor = models.BooleanField(default=False)
    is_contested_by_successor = models.BooleanField(default=False)
    # in case of objection(s), the case is assigned to an arbiter
    time_objection_assigned = models.DateTimeField(default=DEFAULT_DATE)

    def __unicode__(self):
        return 'Ref: %s -- Rev: %s' % (prefixed_user_name(self.referee.user), unicode(self.review))


# NOTE: the system should show appeals with one or two objecting parties only to *senior* referees,
#       and only AFTER the 48 hr term within which parties can object; this to ascertain that
#       all parties concerned have been able to express their view
class Objection(models.Model):
    # objections link a referee to an appeal
    referee = models.ForeignKey(Referee, on_delete=models.PROTECT)
    appeal = models.ForeignKey(Appeal, on_delete=models.PROTECT)
    # NOTE: the appeal contains info on WHO objected
    time_first_viewed = models.DateTimeField(default=DEFAULT_DATE)
    time_decided = models.DateTimeField(default=DEFAULT_DATE)
    # referees must specify the grade that in their opninion is fair
    grade = models.IntegerField(default=0)
    # referees must motivate their decision
    grade_motivation = models.TextField(default='', blank=True)
    # referee may modify the given penalties -- negative scores are in fact BONUS points!
    predecessor_penalty = models.FloatField(default=0)
    successor_penalty = models.FloatField(default=0)
    # parties must acknowledge viewing the verdict within 48 hours after the decision
    time_viewed_by_predecessor = models.DateTimeField(default=DEFAULT_DATE)
    time_viewed_by_successor = models.DateTimeField(default=DEFAULT_DATE)
    # NOTE: the referee whose decision is appealed against is the third party
    time_viewed_by_decider = models.DateTimeField(default=DEFAULT_DATE)
    # parties have 24 hours to respond (incl. making a formal objection)
    time_acknowledged_by_predecessor = models.DateTimeField(default=DEFAULT_DATE)
    time_acknowledged_by_successor = models.DateTimeField(default=DEFAULT_DATE)
    time_acknowledged_by_decider = models.DateTimeField(default=DEFAULT_DATE)
    # both parties must appraise the verdict (on a smiley scale)
    # NOTE: this appraisal may affect the referee's reputation score
    predecessor_appraisal = models.IntegerField(default=0)
    successor_appraisal = models.IntegerField(default=0)
    decider_appraisal = models.IntegerField(default=0)
    # appraisals must also be motivated
    predecessor_motivation = models.TextField(default='', blank=True)
    successor_motivation = models.TextField(default='', blank=True)
    # both parties may raise an objection
    is_contested_by_predecessor = models.BooleanField(default=False)
    is_contested_by_successor = models.BooleanField(default=False)
    is_contested_by_referee = models.BooleanField(default=False)
    # NOTE: in case of objection(s) against the *senior* referee decision,
    #       the case is assigned to an instructor
    time_instructor_assigned = models.DateTimeField(default=DEFAULT_DATE)

    def __unicode__(self):
        return 'Ref: %s -- Ap: %s' % (prefixed_user_name(self.referee.user), unicode(self.appeal))


class LegVideo(models.Model):
    leg_number = models.IntegerField(default=0)  # 0 => not associated with a step
    star_range = models.IntegerField(default=0)  # 0 = none, 1 = low, 2 = high
    language = models.ForeignKey(Language, on_delete=models.PROTECT)
    presenter_initials = models.CharField(max_length=6)
    url = models.CharField(max_length=512, blank=True)
    description = models.TextField(blank=True, default='')
    time_created = models.DateTimeField(default=timezone.now)

    def __unicode__(self):
        return '#%d-Step %d-%s' % (self.id, self.leg_number,
            ['not star-dependent', '1-2 stars', '3-5 stars'][self.star_range])


class PrestoBadge(models.Model):
    # badge must be related to a course
    course = models.ForeignKey(Course, on_delete=models.PROTECT)
    # badge may be linked to either a participant or a referee
    participant = models.ForeignKey(Participant, null=True, blank=True, on_delete=models.SET_NULL)
    referee = models.ForeignKey(Referee, null=True, blank=True, on_delete=models.SET_NULL)
    # number of steps in the estafette, or attainable referee stars
    levels = models.IntegerField(default=0)
    # integer between 1 and levels (indicating partial fulfillment)
    attained_level = models.IntegerField(default=0)
    time_issued = models.DateTimeField(default=timezone.now)
    # timestamp indicating when this badge was (last) rendered as an image
    time_last_rendered = models.DateTimeField(default=DEFAULT_DATE)
    # number of times an image of this badge has been rendered
    rendering_count = models.IntegerField(default=0)
    # timestamp indicating when this badge was (last) verified on the Presto site
    time_last_verified = models.DateTimeField(default=DEFAULT_DATE)
    # number of times this badge has been verified
    verification_count = models.IntegerField(default=0)

    # NOTE: unique constraint permits badges for the same estafette template
    #       as long as participant ID is different, or one as participant and one as referee
    class Meta:
        unique_together = ['course', 'participant', 'referee', 'attained_level']

    def __unicode__(self):
        if self.participant:
            return '#%d-%s (%d/%d) %s' % (self.id, self.course.code,
                self.attained_level, self.levels, unicode(self.participant))
        if self.referee:
            return '#%d-%s REF (%d/%d) %s' % (self.id, self.course.code,
                self.attained_level, self.levels, unicode(self.referee))
        return '#%d-%s - anonymous badge' % (self.id, self.course.code)

    # return badge ID plus all user-relevant badge data in human-readable form as a dictionary
    def as_dict(self):
        d = {'ID': self.id,
             'CC': self.course.code,
             'CN': self.course.name,
             'L': self.levels,
             'AL': self.attained_level,
             'TI': timezone.localtime(self.time_issued).strftime('%Y-%m-%d %H:%M')
            }
        if self.participant:
            p = self.participant
            u = p.student.user
            d['PID'] = p.id
            d['PR'] = self.participant.estafette.estafette.name
            d['TID'] = self.participant.estafette.estafette.template.id
        if self.referee:
            r = self.referee
            u = r.user
            d['RID'] = r.id
            d['PR'] = r.estafette_leg.template.name
            d['TID'] = r.estafette_leg.template.id
        d['FN'] = prefixed_user_name(u)
        d['EM'] = u.email
        return d


class LetterOfAcknowledgement(models.Model):
    # loA must be related to a course estafette
    estafette = models.ForeignKey(CourseEstafette, on_delete=models.PROTECT)
    # LoA may be linked to either a participant or a referee
    participant = models.ForeignKey(Participant, null=True, blank=True, on_delete=models.SET_NULL)
    referee = models.ForeignKey(Referee, null=True, blank=True, on_delete=models.PROTECT)
    time_issued = models.DateTimeField(default=timezone.now)
    # authentication code for verification
    authentication_code = models.CharField(max_length=32, default=random_hex32)
    step_list = models.CharField(max_length=32, blank=True, default='')
    # NOTE: for participant LoA's, the following 5 fields retain their default values
    # timestamps indicate the period in which the user acted as referee
    time_first_case = models.DateTimeField(default=DEFAULT_DATE)
    time_last_case = models.DateTimeField(default=DEFAULT_DATE)
    appeal_case_count = models.IntegerField(default=0)
    extra_hours = models.IntegerField(default=0)
    average_appreciation = models.FloatField(default=0)
    # timestamp indicating when this letter was (last) rendered as a PDF document
    time_last_rendered = models.DateTimeField(default=DEFAULT_DATE)
    # number of times this letter has been rendered
    rendering_count = models.IntegerField(default=0)
    # timestamp indicating when this letter was (last) verified on the Presto site
    time_last_verified = models.DateTimeField(default=DEFAULT_DATE)
    # number of times this letter has been verified
    verification_count = models.IntegerField(default=0)

    def __unicode__(self):
        if self.referee:
            task = 'Referee'
            owner = unicode(self.referee)
        elif self.participant:
            task = 'Participant'
            owner = unicode(self.participant)
        return '#%d-%s %s acknowledgement to %s' % (self.id, unicode(self.estafette), task, owner)

    # return letter ID plus all relevant attributes in human-readable form as a dictionary
    # NOTE: RID = 0 indicates that this is a participant akcnowledgement letter
    def as_dict(self):
        rid = 0
        steps = plural_s(self.estafette.estafette.template.nr_of_legs(), 'step')
        ec = self.estafette.course
        if self.referee:
            u_name = prefixed_user_name(self.referee.user)
            u_mail = self.referee.user.email
            rid = self.referee.id
            steps = self.step_list
        elif self.participant:
            u_name = prefixed_user_name(self.participant.student.user)
            u_mail = self.participant.student.user.email
        else:
            u_name = '(unknown user)'
            u_mail = ''
        return {'CC': ec.code,
                'CN': ec.name,
                'CSD': ec.language.fdate(ec.start_date),
                'CED': ec.language.fdate(ec.end_date),
                'CD': ec.description.strip(),
                'SN': ec.staff_name,
                'SP': ec.staff_position,
                'PR': self.estafette.estafette.name,
                'FN': u_name,
                'EM': u_mail,
                'RID': rid,
                'AC': self.authentication_code,
                'SL': steps,
                'DFC': timezone.localtime(self.time_first_case).strftime('%d %B %Y'),
                'DLC': timezone.localtime(self.time_last_case).strftime('%d %B %Y'),
                'ACC': self.appeal_case_count,
                'XH': self.extra_hours,
                'AA': self.average_appreciation,
                'DI': timezone.localtime(self.time_issued).strftime('%d %B %Y'),
                'RC': self.rendering_count,
                'TLR': timezone.localtime(self.time_last_rendered).strftime('%Y-%m-%d %H:%M')
               }


def course_pq_dir(instance, filename):
    return os.path.join(instance.course.picture_dir, filename)

# stores an image mailed to the settings.PICTURE_QUEUE_MAIL mail address
class QueuePicture(models.Model):
    course = models.ForeignKey(Course, null=True, on_delete=models.CASCADE)
    picture = models.ImageField(upload_to=course_pq_dir)
    time_received = models.DateTimeField(default=timezone.now)
    mail_from_name = models.CharField(max_length=256, blank=True, default='')
    mail_from_address = models.CharField(max_length=256, blank=True, default='')
    mail_subject = models.CharField(max_length=256, blank=True, default='')
    mail_body = models.TextField(default='', blank=True)
    suppressed = models.BooleanField(default=False)

    def __unicode__(self):
        return '#%d-%s from %s (%s)' % (self.id, self.course.code, self.mail_from_address,
            timezone.localtime(self.time_received).strftime('%Y-%m-%d %H:%M'))
