# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-11-20 11:42
from __future__ import unicode_literals

import datetime
from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('presto', '0008_auto_20171024_1709'),
    ]

    operations = [
        migrations.AddField(
            model_name='peerreview',
            name='time_first_download',
            field=models.DateTimeField(default=datetime.datetime(2000, 12, 31, 23, 0, tzinfo=utc)),
        ),
    ]