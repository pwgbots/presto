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

from django.core.management.base import BaseCommand

from django.contrib.auth.models import Group, Permission, User
from django.db.utils import IntegrityError
from presto.models import Profile

# NOTE: provide these constants yourself
SU_NAME = ''
SU_MAIL = ''
SU_FIRST_NAME = ''
SU_LAST_NAME = ''
SU_PASSWORD = ''

class Command(BaseCommand):
    def create_superuser(self, netid, email, first_name, last_name):
        try:
            user1 = User.objects.create_user(netid, email, SU_PASSWORD)
            user1.first_name = first_name
            user1.last_name = last_name
            user1.is_superuser = True
            user1.is_staff = True
            user1.save()
            return user1
        except Exception as e:
            print e
            return None


    def handle(self, *args, **options):
        su = self.create_superuser(SU_NAME, SU_MAIL, SU_FIRST_NAME, SU_LAST_NAME)
        if su is not None:
            print 'Superuser %s created: %s %s (%s)' % (SU_NAME, SU_MAIL, SU_FIRST_NAME, SU_LAST_NAME)
            #Profile.objects.create(user=su)
 