"""
Software developed by Pieter W.G. Bots for the PrESTO project
Code repository: https://github.com/pwgbots/presto
Project wiki: http://presto.tudelft.nl/wiki

Copyright (c) 2022 Delft University of Technology

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is furnished
to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

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

# presto modules
from presto.uiphrases import (
    CALENDAR_NAMES,
    UI_BLACKDICT,
    UI_LANGUAGE_CODES,
    UI_PHRASE_DICT,
    )
from presto.utils import (
    half_points,
    int_to_base36,
    log_message,
    plural_s,
    prefixed_user_name,
    word_count,
    ui_img,
    )

"""
CONSTANTS for this module

These constants are typically used as (initial) values of database fields.
Note that DEFAULT_DATE is imported by most other Presto modules.
"""

# Default date and time formats
SHORT_DATE = '%Y-%m-%d'
SHORT_DATE_TIME = SHORT_DATE + ' %H:%M'

# The default datetime is used throughout Presto to indicate "unspecified".
# NOTE: Do NOT modify this except during new installation of Presto!
tz = timezone.get_current_timezone()
DEFAULT_DATE = timezone.make_aware(
    datetime.strptime('2001-01-01 00:00', SHORT_DATE_TIME)
    )

# Initial value for security key in user session objects:
NO_SESSION_KEY = '(no key)'

# Status codes associated with working in teams:
INVITATION_STATUS = ['PENDING', 'ACCEPTED', 'REJECTED', 'WITHDRAWN']
SEPARATION_STATUS = ['OK', 'PENDING', 'PRONOUNCED', 'RECONCILED']

# Instructors are permitted to be brief in their feedback comments:
MINIMUM_INSTRUCTOR_WORD_COUNT = 10

# Unprocessed appeals and "instructor reviews" will appear in the student view
# this fixed number of days after the end time of a relay:
MAX_DAYS_BEYOND_END_DATE = 90

# Allow students who appealed to respond to appeal decisions even after the end
# time of a relay the response period is limited to a set number of days after
# the appeal case was decided upon.
POST_FINISH_DAYS = 3 

# HTML inserted to mark the end of a review item list to distinguish it from
# the overall review summary and appraisal:
STAR_DIVIDER = """
    <h4 class="ui horizontal divider header">
      &#9734;&#9734;&#9734;&#9734;&#9734;
    </h4>
"""


"""
AUXILIARY FUNCTIONS for this module
"""

def random_hex32():
    """Return a string of 32 random hexadecimal digits."""
    return format(random.getrandbits(128), 'x').zfill(32)

def pq_dir_name():
    """Return a random hex32 with prefix to indicate: Picture Queue files."""
    return 'PQ_' + random_hex32()

def template_dir_name():
    """Return a random hex32 with prefix to indicate: Template files."""
    return 'T_' + random_hex32()

def relay_dir_name():
    """Return a random hex32 with prefix to indicate: Relay files."""
    return 'R_' + random_hex32()

def template_dir(rx, fn):
    """Return path to file fn uploaded for referee exam rx."""
    return os.path.join(instance.estafette_leg.template.upload_dir, filename)

def pq_img_path(pq, fn):
    """Return path to file with name fn submitted to picture queue pq."""
    return os.path.join(pq.course.picture_dir, fn)


"""Django Model classes"""

class Language(models.Model):
    """
    Courses and associated relays can be offered in a specific language.
    
    To provide a consistent user interface for students, standard UI phrases
    are translated into the course language (if supported).
    For performance reasons, phrases are not stored in the database, but
    defined in UI_PHRASE_DICT in Presto module uiphrases.py.
    """
    name = models.CharField(max_length=60)
    code = models.CharField(max_length=10)

    def __str__(self):
        """Return the properties of this language in human-readable format."""
        return ''.join([self.name, ' (', self.code, ')'])

    def nr(self):
        """
        Return a zero-based index for this language, independent of
        its database key.
        """
        return UI_LANGUAGE_CODES.index(self.code)

    def phrase(self, key):
        """
        Return the phrase identified by key in this language.
        
        Return key if it is missing in the phrases dict, or the English phrase
        if no translation exists for this language.
        """
        p_tuple = UI_PHRASE_DICT.get(key, '')
        if not p_tuple:
            return key
        n = self.nr()
        if n < len(p_tuple):
            return p_tuple[n]
        else:
            return p_tuple[0]

    def translate_fdt(self, s):
        """
        Return formatted datetime string s after replacing the English names
        for weekdays and months by their equivalent in this language.
        """
        for name in CALENDAR_NAMES:
            s = s.replace(name, self.phrase(name))
        return s

    def fdate(self, d):
        """
        Return date of datetime d as long format string for this language.
        
        Example: "Wednesday, 1 January 2020". Note that placing a comma after
        the weekday is language-specific, and presently added only for English.
        """
        return ''.join([
            self.phrase(d.strftime('%A')),
            (',' if self.code == 'en-US' else ''),
            d.strftime(' %d '),
            self.phrase(d.strftime('%B')),
            d.strftime(' %Y')
            ])

    def ftime(self, dt):
        """Return datetime d as long format string for this language."""
        return self.fdate(dt) + timezone.localtime(dt).strftime(' %H:%M')

    def penalties_as_text(self, pp, sp):
        """
        Return a nice formulation in this language for a referee sanction.

        Such a sanction defines the penalty points for the predecessor (pp) as
        well as for the successor (sp). Negative values signify bonus points.
        """
        pp = float(pp)
        sp = float(sp)
        if abs(pp) < 0.25 and abs(sp) < 0.25:
            return self.phrase('No_sanctions')
        else:
            pl = []
            if pp >= 0.25:
                pl.append(self.phrase('Penalty_for_predecessor').format(
                    pts=half_points(pp))
                    )
            elif pp <= -0.25:
                pl.append(self.phrase('Bonus_for_predecessor').format(
                    pts=half_points(pp))
                    )
            if sp >= 0.25:
                pl.append(self.phrase('Penalty_for_successor').format(
                    pts=half_points(sp))
                    )
            elif sp <= -0.25:
                pl.append(self.phrase('Bonus_for_successor').format(
                    pts=half_points(sp))
                    )
            return self.phrase('Sanctions') + ', '.join(pl)

    @classmethod
    def get_first_language(self):
        """
        Return the first Language instance, or None if none exist.
        
        Written by Marcel Heijink, inspired by:
            http://david.feinzeig.com/blog/2013/05/12/behold-the-power-of-
            default-how-to-set-the-default-argument-of-a-django-model-field-
            equal-to-a-class-method-using-lambda/
        """
        try:
            return Language.objects.first().id
        except:
            return None


class Role(models.Model):
    """
    Presto users can be authorized for different roles.

    Roles are numbered and are visualized usinc a Semantic UI icon.
    Note that ranks are not "hierarchical" in the sense that higher ranks
    imply having the rights associated with all lower ranks.
    """
    name = models.CharField(max_length=16)
    rank = models.IntegerField()
    icon = models.CharField(max_length=32, default='')

    class Meta:
        """Sort roles by default in ascending rank order."""
        ordering = ('rank', 'name')

    def __str__(self):
        """Return the main properties of this role in human-readable format."""
        return '{rank} - {name}'.format(rank=self.rank, name=self.name)


class Profile(models.Model):
    """
    Each Presto user has an associated Profile to store additional properties.

    Note that except for roles, the properties are based on the authentication
    used at TU Delft. See presto-project/settings.py for details.

    If a user is authenticated via edX, Django's username will be the edX
    identifier, and the user will be prompted to enter his/her first name and
    last name (not mandatory; not verified).
    """
    user = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name='profile'
        )
    roles = models.ManyToManyField(Role)
    is_employee = models.BooleanField(default=False)
    is_edx_user = models.BooleanField(default=False)

    def __str__(self):
        """Return the user properties of this profile."""
        return '{pun} ({un})'.format(
            pun=prefixed_user_name(self.user),
            un=self.user.username
            )

    def has_role(self, role_name):
        """Return True IFF this user is authorized for the specified role."""
        return self.roles.filter(role__name=role_name).count > 0


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Ensure that a profile instance is created when a new user is created."""
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Ensure that a profile is saved when its associated user is saved."""
    instance.profile.save()


class UserSession(models.Model):
    """
    User session data: used for security and for holding status information.
    
    To prevent Cross-Site Request Forgery (CSRF), session keys (32 hex digit
    codes) are routinely "rotated" using an encoder string and a decoder string
    as explained in the Presto module generic.py. 
    The state property is a dictionary (encoded as JSON string) that may hold
    user state variables. It is presently used for tracking whether a demo alias
    is set for the user. If so, the JSON string has two attributes:
    - course_student_id (int): the primary key of the CourseStudent instance
    - alias_name (string): the name entered by the user when prompted
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=64, default=NO_SESSION_KEY)
    decoder = models.CharField(max_length=32, default=random_hex32)
    encoder = models.CharField(max_length=32, default=random_hex32)
    start_time = models.DateTimeField(default=timezone.now)
    last_action = models.DateTimeField(default=timezone.now)
    active_role = models.ForeignKey(
        Role,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
        )
    state = models.TextField(default='{}', blank=True)

    def __str__(self):
        return '{} [{}] {} {}'.format(
            prefixed_user_name(self.user),
            str(self.last_action).encode('utf-8').decode('utf-8')[:19],
            self.session_key,
            self.state
            )


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

    def __str__(self):
        return '{}--{}'.format(self.code, self.name)

    def title(self):
        return '<em>{}</em> ({})'.format(self.name, self.code)


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

    def __str__(self):
        if self.dummy_index < 0:
            return '#{}-{}: Course instructor ({})'.format(
                self.id,
                self.course.code,
                prefixed_user_name(self.user)
                )
        if self.dummy_index > 0:
            index = ' ({})'.format(self.dummy_index)
        else:
            index = ''
        return '#{}-{}: {}{}'.format(
            self.id,
            self.course.code,
            prefixed_user_name(self.user),
            index
            )

    def dummy_name(self):
        if self.dummy_index > 0:
            index = ' (dummy # {})'.format(self.dummy_index)
        else:
            index = ''
        return prefixed_user_name(self.user) + index

    def pin(self):
        return str(
            int(md5((self.particulars + str(self.dummy_index)).encode('ascii', 'ignore')
                    ).hexdigest()[4:11], 16))[:4].zfill(4)


class Item(models.Model):
    """
    Items are used to structure a review to appraise various aspects of a work.
    
    Items may be appraised on different scales, specified by a string according
    to this syntax:

      rating:(range):(symbol)                  where (symbol) may be "star" or "heart"
      likert:(range):(low label):(high label)  where labels express meaning of the scale ends
      score:(range):(style)                    where (style) may be "input", "dropdown" or "menu"
      icons:(icon 1|color):(icon 2|color): ... where (icon N) must be a valid Semantic UI icon name
      options:(option 1):(option 2): ...       where (option N) must be a non-empty string

    NOTE: (range) denotes highest value (integer > 1); the lower end of a range
          is by definition 1.
    """
    number = models.IntegerField(default=1)
    name = models.CharField(max_length=128)
    instruction = models.TextField(blank=True, default='')
    word_count = models.IntegerField(default=0)
    appraisal = models.CharField(max_length=128, blank=True, default='')
    no_comment = models.BooleanField(default=False)

    class Meta:
        ordering = ['number']

    def __str__(self):
        return '#{}-{}. {}'.format(self.id, self.number, self.name)

    def as_html(self):
        return '<h4>{}. {}</h4>{}'.format(
            self.number,
            self.name,
            self.instruction
            )

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
    creator = models.ForeignKey(
        User,
        related_name='evt_creator',
        on_delete=models.PROTECT
        )
    editors = models.ManyToManyField(
        User,
        related_name='evt_editors',
        blank=True
        )
    last_editor = models.ForeignKey(
        User,
        related_name='evt_last_editor',
        null=True,
        on_delete=models.SET_NULL
        )
    time_created = models.DateTimeField(default=timezone.now)
    time_last_edit = models.DateTimeField(default=timezone.now)
    published = models.BooleanField(default=False)

    def __str__(self):
        return 'QT: ' + self.name


class EstafetteTemplate(models.Model):
    name = models.CharField(max_length=128, unique=True)
    description = models.TextField(blank=True, default='')
    default_rules = models.TextField(blank=True, default='')
    # every template has own subdirectory (T_ plus 32 hex digits) in the uploads directory
    upload_dir = models.CharField(
        max_length=34,
        unique=True,
        default=template_dir_name
        )
    creator = models.ForeignKey(
        User,
        related_name='est_creator',
        on_delete=models.PROTECT
        )
    editors = models.ManyToManyField(
        User,
        related_name='est_editors',
        blank=True
        )
    last_editor = models.ForeignKey(
        User,
        related_name='est_last_editor',
        null=True,
        on_delete=models.SET_NULL
        )
    time_created = models.DateTimeField(default=timezone.now)
    time_last_edit = models.DateTimeField(default=timezone.now)
    published = models.BooleanField(default=False)

    def __str__(self):
        return 'ET: ' + self.name

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
            nn = d['name'] + ' ({})'.format(n)
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
        log_message(
            'Initialized template {} from JSON string'.format(self.name, user)
            )


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
                nx = ['file{}'.format(n), nx[0]]
                n += 1
            fl.append({
                'prompt': pr[0],
                'name': nx[0],
                'types': '.' + ',.'.join(nx[1].split(','))
                })
    except Exception as e:
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

    def __str__(self):
        return 'EL#{}: {} (#{} in {})'.format(
            self.id,
            self.name,
            self.number,
            self.template.name
            )
    
    def title(self, step):
        return '{} {} &ndash; {}'.format(step, self.number, self.name)

    def file_list(self):
        return string_to_file_list(self.required_files)

    # returns review instruction plus all review item instructions as one HTML string
    def complete_review_instruction(self):
        cri = (''.join([ri.as_html() for ri in self.review_items.all()])
            + STAR_DIVIDER + self.review_instruction)
        # check whether HTML contains more than just empty paragraphs (as generated by Quill)
        if cri.replace('<p><br></p>', ''):
            return ui_img(cri)
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
            'time_created': timezone.localtime(self.time_created).strftime(
                SHORT_DATE_TIME
                ),
            'time_last_edit': timezone.localtime(self.time_last_edit).strftime(
                SHORT_DATE_TIME
                ),
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

    def __str__(self):
        return '{} (T: {})'.format(self.name, self.template.name)

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

    def __str__(self):
        return '#{}-{} ({})'.format(
            self.id,
            self.original_name,
            str(self.estafette)
            )


class EstafetteCase(models.Model):
    estafette = models.ForeignKey(Estafette, on_delete=models.PROTECT)
    letter = models.CharField(max_length=1)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True, default='')
    required_keywords = models.CharField(max_length=512, blank=True)
    upload = models.ForeignKey(
        CaseUpload,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
        )
    creator = models.ForeignKey(
        User,
        related_name='ec_creator',
        on_delete=models.PROTECT
        )
    last_editor = models.ForeignKey(
        User,
        related_name='ec_editor',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
        )
    time_created = models.DateTimeField(default=timezone.now)
    time_last_edit = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ('estafette', 'letter')
        unique_together = ['estafette', 'letter']

    def __str__(self):
        return 'EC: {} ({}) {}'.format(
            self.name,
            self.letter,
            self.estafette.name
            )

    def title(self, case):
        return '{} {}: {}'.format(case, self.letter, self.name)


class CourseEstafette(models.Model):
    course = models.ForeignKey(Course, on_delete=models.PROTECT)
    estafette = models.ForeignKey(Estafette, on_delete=models.PROTECT)
    suffix = models.CharField(max_length=8, default='', blank=True)
    start_time = models.DateTimeField(default=DEFAULT_DATE)
    deadline = models.DateTimeField(default=DEFAULT_DATE)
    review_deadline = models.DateTimeField(default=DEFAULT_DATE)
    end_time = models.DateTimeField(default=DEFAULT_DATE)
    actual_rules = models.TextField(blank=True, default='')
    questionnaire_template = models.ForeignKey(
        QuestionnaireTemplate,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
        )
    minimum_partners = models.IntegerField(default=0)
    maximum_partners = models.IntegerField(default=0)
    final_reviews = models.IntegerField(default=0)
    minimum_appraisal_word_count = models.IntegerField(default=30)
    minimum_appeal_word_count = models.IntegerField(default=20)
    with_review_clips = models.BooleanField(default=False)
    with_badges = models.BooleanField(default=False)
    with_referees = models.BooleanField(default=False)
    allow_questions = models.BooleanField(default=False)
    # scoring system:
    #  0 = relative differential;
    #  1 = absolute with differential bonus
    #  2 = absolute plus relative differential on predecessor's work
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
        """Set UNIQUE constraints and default sorting criteria."""
        unique_together = ['course', 'estafette', 'suffix']
        ordering = ('end_time', 'start_time')

    def __str__(self):
        """Return a string with properties identifying this course."""
        return '#{}-{}{}'.format(
            self.id,
            self.title_text(),
            '--DELETED' if self.is_deleted else ''
            )

    def title(self):
        """Return the title of this course relay as HTML."""
        return self.course.code + ' <em>' + self.estafette.name + '</em>' + (
            ' (' + self.suffix + ')' if self.suffix else ''
            )
    
    def title_text(self):
        """Return the title of this course relay as plain text."""
        return self.course.code + ' ' + self.estafette.name + (
            ' (' + self.suffix + ')' if self.suffix else ''
            )
    
    def next_deadline(self):
        """
        Return a 3-tuple (next deadline, phrase for this deadline, color name).
        
        The next deadline is a datetime object, the phrase a key in the UI
        phrases dict, andcolor name denotes a Semantic UI color that reflects
        how pressing the deadline is.
        """
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
        if self.suspended():
            color = 'black'
        lang = self.course.language
        return {
            'time': lang.ftime(next_dl),
            'label': lang.phrase(dl_phrase),
            'color': color
            }

    # returns a list of leg numbers for this estafette in ascending order (= default ordering)
    def leg_numbers(self):
        return EstafetteLeg.objects.filter(
            template=self.estafette.template
            ).value_list('number', flat=True)
    
    # returns TRUE if final reviews should become available only AFTER the
    # assignment deadline
    def final_reviews_at_end(self):
        # this setting is specified in the case set description
        match = re.search(r'FINAL\s+REVIEWS\s+AT\s+END', self.estafette.description)
        if match:
            log_message('Final reviews at end')
            return True
        log_message('Final reviews a.s.a.p.')
        return False

    # returns TRUE if relay is set to "suspended"
    def suspended(self):
        # this setting is specified in the case set description
        match = re.search(r'SUSPENDED', self.estafette.description)
        if match:
            log_message('Relay {} has been suspended'.format(self.title_text()))
            return True
        return False

    # returns TRUE if participants may see the points scored for final reviews
    def show_final_review_scores(self):
        # this setting is specified in the case set description
        match = re.search(r'SHOW\s+FINAL\s+REVIEW\s+SCORES', self.estafette.description)
        if match:
            log_message('Final review scores for {} are shown'.format(self.title_text()))
            return True
        return False

    # returns a dict {leg number: date-time} with bonus deadlines per step
    def bonus_deadlines(self):
        bd = {}

        # check if default bonus deadline is overridden in estafette description
        match = re.search(r'BONUS:([0-9\s]+)', self.estafette.description)
        if match:
            days = [int(x) for x in re.findall(r'\d+', match.group(0))]
            legs = self.estafette.template.nr_of_legs()
            tzi = timezone.get_current_timezone()
            sdt = self.start_time.astimezone(tzi)
            et = sdt.replace(hour=17, minute=30)
            # iterate over all legs
            lnr = 0
            for d in days:
                et += timedelta(days=d) 
                lnr += 1
                bd[lnr] = et
            return bd    

        days = (self.deadline - self.start_time).days - 2
        # three 6-hour blocks per day, skipping midnight - 6 a.m. as workable time 
        blocks = days * 3
        legs = self.estafette.template.nr_of_legs()
        tzi = timezone.get_current_timezone()
        sdt = self.start_time.astimezone(tzi)
        sh = int(sdt.hour / 6) * 6
        be0 = sdt.replace(hour=sh)
        # speed bonus applies only if total duration in blocks >= # legs + 3, as then
        # there will be 2 blocks for leg 1 and then 1 block per leg, leaving 2 blocks to the deadline
        if self.bonus_per_step and blocks > legs + 2:
            # allow 1/(N+1) blocks per leg 2, ..., N; this leaves more time for leg 1
            blocks_per_leg = int(blocks / (legs + 1))
            # initialize block_ends as the end of the block prior to the starting time
            block_ends = [be0] * (blocks + 1)
            # use a 6-hour increment for the deadline
            one_block = timedelta(seconds=3600*6)
            # prepare for time differences due to Daylight Saving Time (DST)
            one_hour = timedelta(seconds=3600)
            # fill the list with next block ends
            for i in range(1, blocks + 1):
                block_ends[i] = block_ends[i - 1] + one_block
                h = block_ends[i].astimezone(tzi).hour
                # compensate in case time shifts 1 hour due to DST
                if h in [5, 11, 17, 23]:
                    block_ends[i] += one_hour
                elif h in [1, 7, 13, 19]:
                    block_ends[i] -= one_hour
                # skip the blocks ending at 6 a.m.
                if block_ends[i].astimezone(tzi).hour == 6:
                    block_ends[i] += one_block
            # calculate the block number for the end of step 1
            block = blocks - (legs - 1) * blocks_per_leg
            # iterate over all legs
            for el in EstafetteLeg.objects.filter(template=self.estafette.template):
                bd[el.number] = block_ends[block]
                # avoid ambiguities around midnight: subtract one second 
                if bd[el.number].astimezone(tzi).hour == 0 and bd[el.number].astimezone(tzi).minute == 0:
                    # log_message('before: ' + bd[el.number].strftime('%A %d-%m %H:%M:%S'))
                    bd[el.number] -= timedelta(seconds=1)
                    # log_message('after: ' + bd[el.number].strftime('%A %d-%m %H:%M:%S'))
                # advance to next block
                block += blocks_per_leg 
        return bd

    # returns string stating the number of reviews that have been appealed,
    # and appeals that have been objected against, and not yet decided (and acknowledged).
    # returns empty string if none, or if a specified number of days have passed since the relay end time
    def pending_decisions(self):
        if self.end_time + timedelta(days=MAX_DAYS_BEYOND_END_DATE) < timezone.now():
            return ''
        # allow a few days for participants to respond to referee decisions
        adt = timezone.now() - timedelta(days=POST_FINISH_DAYS)
        # pending appeals are: (1) appealed reviews that have not been taken on by a referee yet
        ap_cnt = PeerReview.objects.filter(reviewer__estafette=self,
            is_appeal=True, time_appeal_assigned=DEFAULT_DATE).count()
        # (2) assigned appeals that have not been decided yet
        ap_cnt += Appeal.objects.filter(review__reviewer__estafette=self,
            time_decided=DEFAULT_DATE).count()
        # pending objections are: (1) decided appeals that are contested appeals and have not been assigned
        ob_cnt = Appeal.objects.filter(review__reviewer__estafette=self,
            time_decided__gt=DEFAULT_DATE, time_objection_assigned=DEFAULT_DATE
            ).exclude(is_contested_by_predecessor=False, is_contested_by_successor=False).count()
        # (2) assigned objections that have not been decided yet
        ob_cnt += Objection.objects.filter(time_decided=DEFAULT_DATE,
            appeal__review__reviewer__estafette=self).count()
        # potential objections: recently (!) decided appeals that have NOT been contested
        pob_cnt = Appeal.objects.filter(review__reviewer__estafette=self, time_decided__gt=adt,
            is_contested_by_predecessor=False, is_contested_by_successor=False).count()
        ssl = []
        if ap_cnt:
            ssl.append(plural_s(ap_cnt, 'pending appeal'))
        if ob_cnt:
            ssl.append(plural_s(ob_cnt, 'pending objection'))
        if pob_cnt:
            ssl.append(plural_s(pob_cnt, 'potential objection'))
        if ssl:
            ssl = '; '.join(ssl)
            log_message('Pending decisions for ' + str(self) + ': ' + ssl)
            return ssl
        return ''

    # returns a (most likely!) unique five-digit base36 code for this estafette
    def demonstration_code(self):
        # only the DEMO course has a demonstration course
        if self.course.code != 'DEMO':
            return ''
        # get a *deterministic* 33-digit hash with a leading non-zero digit
        hx = md5(str(self).encode('ascii', 'ignore')).hexdigest()
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
        hx = md5(str(self).encode('ascii', 'ignore') * 3).hexdigest()
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

    def __str__(self):
        return '#{}-{}-{}{}'.format(
            self.id,
            str(self.student),
            str(self.estafette),
            '--DELETED' if self.deleted else ''
            )

    def shorthand(self):
        return str(self.student)

    # returns number of steps and reviews done as a fast proxy for participant progress
    # NOTE: this proxy is used only in student.py
    def progress(self):
        # NOTE: use the leg number of te last assignment, as participants may have
        #       been part of a team without uploading assignments themselves
        a = Assignment.objects.filter(participant=self).last()
        steps = a.leg.number if a else 0
        return steps + PeerReview.objects.filter(reviewer=self).count()

    # returns string stating the number of reviews that have been appealed,
    # and appeals that have been objected against, and not yet decided (and acknowledged).
    # returns empty string if none, or if too many days have passed since the relay end time
    def pending_decisions(self):
        r = self.estafette
        if r.end_time + timedelta(days=MAX_DAYS_BEYOND_END_DATE) < timezone.now():
            return ''
        # allow a few days for participants to respond to referee decisions
        adt = timezone.now() - timedelta(days=POST_FINISH_DAYS)
        # pending appeals are: (1) appealed RECEIVED reviews that have not been taken on by a referee yet
        ap_cnt = PeerReview.objects.filter(assignment__participant=self,
            is_appeal=True, time_appeal_assigned=DEFAULT_DATE).count()
        # (2) appealed GIVEN reviews that have not been taken on by a referee yet
        ap_cnt += PeerReview.objects.filter(reviewer=self,
            is_appeal=True, time_appeal_assigned=DEFAULT_DATE).count()
        """
        # (3) assigned appeals that have not been decided yet
        ap_cnt += Appeal.objects.filter(time_decided=DEFAULT_DATE)exclude(review__reviewer__ne=self, ).count()
        # pending objections are: (1) decided appeals that are contested appeals and have not been assigned
        ob_cnt = Appeal.objects.filter(time_decided__gt=DEFAULT_DATE, time_objection_assigned=DEFAULT_DATE
            ).exclude(is_contested_by_predecessor=False, is_contested_by_successor=False).count()
        # (2) assigned objections that have not been decided yet
        ob_cnt += Objection.objects.filter(time_decided=DEFAULT_DATE).count()
        # potential objections: recently (!) decided appeals that have NOT been contested
        pob_cnt = Appeal.objects.filter(review__reviewer__estafette=self, time_decided__gt=adt,
            is_contested_by_predecessor=False, is_contested_by_successor=False).count()
        """
        ssl = []
        if ap_cnt:
            ssl.append(plural_s(ap_cnt, 'pending appeal'))
        if ob_cnt:
            ssl.append(plural_s(ob_cnt, 'pending objection'))
        if pob_cnt:
            ssl.append(plural_s(pob_cnt, 'potential objection'))
        if ssl:
            return '; '.join(ssl)
        return ''


class PartnerInvitation(models.Model):
    initiator = models.ForeignKey(
        Participant,
        related_name='initiating_partner',
        on_delete=models.PROTECT
        )
    partner = models.ForeignKey(
        Participant,
        related_name='invited_partner',
        on_delete=models.PROTECT
        )
    time_invited = models.DateTimeField(default=timezone.now)
    time_response = models.DateTimeField(default=DEFAULT_DATE)
    response_text = models.TextField(default='', blank=True)
    time_withdrawn = models.DateTimeField(default=DEFAULT_DATE)
    status = models.IntegerField(default=0)

    def __str__(self):
        return '#{}-{}-{}: {}'.format(
            self.id,
            str(self.participant),
            str(self.student),
            INVITATION_STATUS[self.status]
            )


class Partner(models.Model):
    initiator = models.ForeignKey(
        Participant,
        related_name='initiating_participant',
        on_delete=models.PROTECT
        )
    partner = models.ForeignKey(Participant, on_delete=models.PROTECT)
    time_partnered = models.DateTimeField(default=timezone.now)
    status = models.IntegerField(default=0)
    time_separation_filed = models.DateTimeField(default=DEFAULT_DATE)
    separation_motivation = models.TextField(default='', blank=True)
    time_separated = models.DateTimeField(default=DEFAULT_DATE)
    separated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.CASCADE
        )
    instructor_comment = models.TextField(default='', blank=True)
    
    def __str__(self):
        return '#{}-{}-{}: {}'.format(
            self.id,
            str(self.student),
            str(self.participant),
            SEPARATION_STATUS[self.status]
            )


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

    # NOTE: each participant can have only one assignment per leg, but this work
    #       may be cloned once
    class Meta:
        unique_together = ['participant', 'leg', 'clone_of']

    def __str__(self):
        if self.time_uploaded == DEFAULT_DATE:
            suffix = ''
        else:
            suffix = ' ({})'.format(
                timezone.localtime(self.time_uploaded).strftime(SHORT_DATE_TIME)
                )
            if self.clone_of != None:
                if self.is_selfie:
                    suffix += ' SELFIE'
                else:
                    suffix += ' CLONE'
            if self.is_rejected:
                suffix += ' [REJ]'
            if self.successor != None:
                suffix += ' => ' + self.successor.participant.shorthand()
        return '#{}-{}{}-{}{}'.format(
            self.pk,
            self.leg.number,
            self.case.letter,
            str(self.participant),
            suffix
            )

    # returns the bonus deadline as a course-language-formatted date-time string if this assignment
    # was submitted before its bonus_per_step deadline, or if it still can be sumbitted on time
    # (taking into account the enforced waiting time); otherwise returns an empty string 
    def on_time_for_bonus(self, min_to_wait = 0):
        # get the course relay
        r = self.participant.estafette
        if not r.bonus_per_step:
            return ''

        # if the assignment has been sumbitted, check the time it was uploaded
        if self.time_uploaded != DEFAULT_DATE:
            t = self.time_uploaded
        else:
            t = timezone.now()

        # NOTE: As of 15-11-2019, the speed bonus deadlines per step are fixed
        if r.start_time > timezone.make_aware(datetime.strptime('2019-11-15', SHORT_DATE)):
            # get the bonus deadlines per step as a dictionary {step number: date-time}
            bd = r.bonus_deadlines().get(self.leg.number, False)
            if not bd:
                return '' 
        else:
            # this is the legacy ("floating horizon") bonus deadline computation
            # (1) calculate time between assigned and assignments deadline MINUS 24 hours
            no_bonus_delta = timedelta(days=1)
            
            # NOTE: Per 01-01-2019, the speed bonus term was shortened to T - MAX(T/4, 24h), i.e.,
            #       the time available for assignments minus either 25% of the time, or 1 full day.
            if r.start_time < timezone.make_aware(datetime.strptime('2019-01-01', SHORT_DATE)):
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

        # allow for 1 grace minute
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

    def __str__(self):
        return '{}-{}: {} ({})'.format(
            str(self.assignment),
            self.file_name,
            self.upload_file.name,
            timezone.localtime(self.time_uploaded).strftime(SHORT_DATE_TIME)
            )


# Each download of an uploaded file (of zipped set) is registered.
# This allows checking per user whether s/he has indeed "seen" a file
class UserDownload(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    time_downloaded = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['time_downloaded']

    def __str__(self):
        return '{}: {} downloaded {}'.format(
            timezone.localtime(self.time_downloaded).strftime(SHORT_DATE_TIME),
            prefixed_user_name(self.user),
            str(self.assignment)
            )


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
    # Scan may detect improper language, or mismatch with course language.
    improper_language = models.TextField(default='', blank=True)
    is_appeal = models.BooleanField(default=False)
    time_acknowledged = models.DateTimeField(default=DEFAULT_DATE)
    time_appeal_assigned = models.DateTimeField(default=DEFAULT_DATE)

    def __str__(self):
        if self.time_submitted == DEFAULT_DATE:
            ts = ''
        else:
            ts = ' ({})'.format(
                timezone.localtime(self.time_submitted).strftime(SHORT_DATE_TIME)
                )
        if int(self.grade) < 1:
            gr = '?'
        else:
            gr = str(self.grade)
        if self.is_rejection:
            gr += ' [REJECT]'
        elif self.final_review_index:
            gr += ' [FINAL-{}]'.format(self.final_review_index)
        if self.time_appraised == DEFAULT_DATE:
            ta = ''
        else:
            ta = ' ({})'.format(
                timezone.localtime(self.time_appraised).strftime(SHORT_DATE_TIME)
                )
        if self.appraisal < 1:
            ap = '-?'
        else:
            ap = '-' + str(self.appraisal)
        if self.is_appeal:
            ap += ' [APPEAL]'
        return '#{}-{}: {}{} - {}{}{}{}'.format(
            self.id,
            str(self.reviewer),
            self.assignment.case.letter,
            self.assignment.leg.number,
            gr,
            ts,
            ap,
            ta
            )

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
            'min_words': (
                min(MINIMUM_INSTRUCTOR_WORD_COUNT, i.word_count) if instr_rev
                else i.word_count
                )
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
        # not complete if no star rating or motivation too short
        wcnt = word_count(self.grade_motivation)
        if int(self.grade) == 0 or wcnt < min_w:
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
        text = ' '.join(
            [ir.comment for ir in ItemReview.objects.filter(review=self)]
            )
        text = ' '.join([
            text,
            self.grade_motivation,
            self.appraisal_comment,
            self.improvement_appraisal_comment
            ])
        text = strip_tags(
            text.lower().replace('.', ' ').replace(',', ' ').replace(
                ';', ' ').replace('!', ' ').replace('?', ' ')
            )
        # Get the course estafette language.
        lang = self.reviewer.student.course.language
        # Check whether the text appears to be in that language.
        # If probability too low, return detect_langs dict as string.
        try:
            msg = ''
            dlc = detect(text)
            if dlc != lang.code.split('-')[0]:
                msg = '{} instead of {}'.format(dlc, lang.code)
                raise ValueError(msg)
        except Exception as e:
            if not msg:
                msg = 'scan error'
            self.improper_language = msg
            self.save()
            return '{} -- {}'.format(self, str(e))
        
        # If the language is OK, scan for blacklisted words.
        real_matches = []
        blacklist = UI_BLACKDICT[lang.code]
        matches = []
        for word in blacklist:
            if word in text:
                matches.append(word)
        if matches:
            # Ignore matches that also occur in the assignment itself...
            text = ' '.join([
                self.assignment.leg.description,
                self.assignment.case.name,
                self.assignment.case.description
                ])
            text = strip_tags(
                text.lower().replace('.', ' ').replace(',', ' ').replace(
                    ';', ' ').replace('!', ' ').replace('?', ' ')
                )
            # ... so only retain words not used by the instructor.
            for word in matches:
                if not (word in text):
                    real_matches.append(word)
        # Record the improper language issue for this review.
        if real_matches:
            msg = ', '.join(real_matches)
            self.improper_language = msg
            self.save()
            return '{} -- {}'.format(self, msg)
        # No issues? Then erase issue if set during a prior scan.
        if self.improper_language:
            self.improper_language = ''
            self.save()
        return False


class ItemReview(models.Model):
    """
    Item reviews are user responses to a specific peer review item.
    """
    review = models.ForeignKey(PeerReview, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.PROTECT)
    comment = models.TextField(blank=True, default='')
    rating = models.IntegerField(blank=True, default=0)

    def __str__(self):
        return '#{}-{}'.format(self.id, str(self.review))


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

    def __str__(self):
        return '#{}-Exam: {}'.format(self.id, str(self.estafette_leg))


class Referee(models.Model):
    # users qualify themselves, hence not CourseStudent or Participant
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # qualification pertains to one specific step in an estafette
    estafette_leg = models.ForeignKey(EstafetteLeg, on_delete=models.CASCADE)
    # NOTE: passed exam may be NULL for instructors
    passed_exam = models.ForeignKey(
        RefereeExam,
        null=True,
        blank=True,
        on_delete=models.PROTECT
        )
    time_qualified = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return '{} - {}'.format(
            prefixed_user_name(self.user),
            str(self.estafette_leg)
            )


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

    def __str__(self):
        return 'Ref: {} -- Rev: {}'.format(
            prefixed_user_name(self.referee.user),
            str(self.review)
            )


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

    def __str__(self):
        return 'Ref: {} -- Ap: {}'.format(
            prefixed_user_name(self.referee.user),
            str(self.appeal)
            )


class LegVideo(models.Model):
    leg_number = models.IntegerField(default=0)  # 0 => not associated with a step
    star_range = models.IntegerField(default=0)  # 0 = none, 1 = low, 2 = high
    language = models.ForeignKey(Language, on_delete=models.PROTECT)
    presenter_initials = models.CharField(max_length=6)
    url = models.CharField(max_length=512, blank=True)
    description = models.TextField(blank=True, default='')
    time_created = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return '#{}-Step {}-{}'.format(
            self.id,
            self.leg_number,
            ['not star-dependent', '1-2 stars', '3-5 stars'][self.star_range]
            )


class PrestoBadge(models.Model):
    # badge must be related to a course
    course = models.ForeignKey(Course, on_delete=models.PROTECT)
    # badge may be linked to either a participant or a referee
    participant = models.ForeignKey(
        Participant,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
        )
    referee = models.ForeignKey(
        Referee,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
        )
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

    def __str__(self):
        if self.participant:
            return '#{}-{} ({}/{}) {}'.format(
                self.id,
                self.course.code,
                self.attained_level,
                self.levels,
                str(self.participant)
                )
        if self.referee:
            return '#{}-{} REF ({}/{}) {}'.format(
                self.id,
                self.course.code,
                self.attained_level,
                self.levels,
                str(self.referee)
                )
        return '#{}-{} - anonymous badge'.format(self.id, self.course.code)

    # return badge ID plus all user-relevant badge data in human-readable form as a dictionary
    def as_dict(self):
        d = {
            'ID': self.id,
            'CC': self.course.code,
            'CN': self.course.name,
            'L': self.levels,
            'AL': self.attained_level,
            'TI': timezone.localtime(self.time_issued).strftime(SHORT_DATE_TIME)
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
    participant = models.ForeignKey(
        Participant,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
        )
    referee = models.ForeignKey(
        Referee,
        null=True,
        blank=True,
        on_delete=models.PROTECT
        )
    time_issued = models.DateTimeField(default=timezone.now)
    # authentication code for verification
    authentication_code = models.CharField(max_length=32, default=random_hex32)
    step_list = models.CharField(max_length=32, blank=True, default='')
    # NOTE: For participant LoA's, the following 5 fields
    #       retain their default values.
    # Timestamps indicate the period in which the user acted as referee.
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

    def __str__(self):
        if self.referee:
            task = 'Referee'
            owner = str(self.referee)
        elif self.participant:
            task = 'Participant'
            owner = str(self.participant)
        return '#{}-{} {} acknowledgement to {}'.format(
            self.id,
            str(self.estafette),
            task,
            owner
            )

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
        return {
            'CC': ec.code,
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
            'TLR': timezone.localtime(self.time_last_rendered).strftime(
                SHORT_DATE_TIME
                )
            }


class QueuePicture(models.Model):
    """
    Stores an image mailed to the settings.PICTURE_QUEUE_MAIL mail address.
    """
    course = models.ForeignKey(Course, null=True, on_delete=models.CASCADE)
    picture = models.ImageField(upload_to=pq_img_path)
    time_received = models.DateTimeField(default=timezone.now)
    mail_from_name = models.CharField(max_length=256, blank=True, default='')
    mail_from_address = models.CharField(max_length=256, blank=True, default='')
    mail_subject = models.CharField(max_length=256, blank=True, default='')
    mail_body = models.TextField(default='', blank=True)
    suppressed = models.BooleanField(default=False)

    def __str__(self):
        return '#{}-{} from {} ({})'.format(
            self.id,
            self.course.code,
            self.mail_from_address,
            timezone.localtime(self.time_received).strftime(SHORT_DATE_TIME)
            )

class Announcement(models.Model):
    """
    Announcements to be displayed under specified conditions.
    
    Display may be limited to a course, a course relay, and specific user role.
    Display may be dismissable. In that case, the announcement ID is added to
    the "dismissals" field of the user's session status.
    """
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField(default='', blank=True)
    time_announced = models.DateTimeField(default=timezone.now)
    time_last_edited = models.DateTimeField(default=timezone.now)
    time_cancelled =  models.DateTimeField(default=DEFAULT_DATE)
    course = models.ForeignKey(Course, null=True, on_delete=models.CASCADE)
    course_relay = models.ForeignKey(
        CourseEstafette,
        null=True,
        on_delete=models.CASCADE
        )
    user_role = models.ForeignKey(Role, null=True, on_delete=models.CASCADE)
    # Urgent announcements are displayed as a warning, otherwise as information.
    urgent = models.BooleanField(default=True)
    dismissable = models.BooleanField(default=True)
    

class Question(models.Model):
    """
    Questions may be posed by participants when this relay option is set.
    """
    poser = models.ForeignKey(Participant, on_delete=models.CASCADE)
    assignment = models.ForeignKey(
        Assignment, null=True, blank=True, on_delete=models.CASCADE)
    content = models.TextField(default='', blank=True)
    time_posed = models.DateTimeField(default=timezone.now)
    instructor = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.CASCADE)
    reply = models.TextField(default='', blank=True)
    time_answered = models.DateTimeField(default=DEFAULT_DATE)

