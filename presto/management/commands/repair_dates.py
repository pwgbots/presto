# Software developed for the PrESTO project -- see http://presto.tudelft.nl/wiki
# Copyright (c) 2017-2018 by Pieter Bots. All rights reserved.

from django.conf import settings
from django.core.management.base import BaseCommand

from presto.models import UserDownload, PeerReview, DEFAULT_DATE

# set time_first_download field for peer reviews for which this field is presently lacking
class Command(BaseCommand):

    def handle(self, *args, **options):
        qset  = PeerReview.objects.filter(time_first_download=DEFAULT_DATE)
        print(qset.count(), ' peer reviews without first download time field')
        n = 0
        for pr in qset:
            ud = UserDownload.objects.filter(user=pr.reviewer.student.user, assignment=pr.assignment)
            if ud:
                ud = ud.first()
                pr.time_first_download = ud.time_downloaded
                pr.save()
                n += 1
        print(n, ' peer reviews updated')
