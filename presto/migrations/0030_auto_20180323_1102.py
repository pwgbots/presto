# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-03-23 10:02
from __future__ import unicode_literals

import datetime
from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('presto', '0029_auto_20180322_1620'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='staff_name',
            field=models.CharField(blank=True, default='', max_length=128),
        ),
        migrations.AddField(
            model_name='course',
            name='staff_position',
            field=models.CharField(blank=True, default='', max_length=128),
        ),
        migrations.AddField(
            model_name='letterofaknowledgement',
            name='time_last_verified',
            field=models.DateTimeField(default=datetime.datetime(2000, 12, 31, 23, 0, tzinfo=utc)),
        ),
        migrations.AddField(
            model_name='letterofaknowledgement',
            name='verification_count',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='prestobadge',
            name='time_last_verified',
            field=models.DateTimeField(default=datetime.datetime(2000, 12, 31, 23, 0, tzinfo=utc)),
        ),
        migrations.AddField(
            model_name='prestobadge',
            name='verification_count',
            field=models.IntegerField(default=0),
        ),
    ]
