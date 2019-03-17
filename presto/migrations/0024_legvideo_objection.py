# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-01-22 13:03
from __future__ import unicode_literals

import datetime
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('presto', '0023_auto_20180118_1357'),
    ]

    operations = [
        migrations.CreateModel(
            name='LegVideo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('leg_number', models.IntegerField(default=0)),
                ('star_range', models.IntegerField(default=0)),
                ('presenter_initials', models.CharField(max_length=6)),
                ('url', models.CharField(blank=True, max_length=512)),
                ('description', models.TextField(blank=True, default='')),
                ('time_created', models.DateTimeField(default=django.utils.timezone.now)),
                ('language', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='presto.Language')),
            ],
        ),
        migrations.CreateModel(
            name='Objection',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('time_first_viewed', models.DateTimeField(default=datetime.datetime(2000, 12, 31, 23, 0, tzinfo=utc))),
                ('time_decided', models.DateTimeField(default=datetime.datetime(2000, 12, 31, 23, 0, tzinfo=utc))),
                ('grade', models.IntegerField(default=0)),
                ('grade_motivation', models.TextField(blank=True, default='')),
                ('predecessor_penalty', models.FloatField(default=0)),
                ('successor_penalty', models.FloatField(default=0)),
                ('time_viewed_by_predecessor', models.DateTimeField(default=datetime.datetime(2000, 12, 31, 23, 0, tzinfo=utc))),
                ('time_viewed_by_successor', models.DateTimeField(default=datetime.datetime(2000, 12, 31, 23, 0, tzinfo=utc))),
                ('time_viewed_by_decider', models.DateTimeField(default=datetime.datetime(2000, 12, 31, 23, 0, tzinfo=utc))),
                ('time_acknowledged_by_predecessor', models.DateTimeField(default=datetime.datetime(2000, 12, 31, 23, 0, tzinfo=utc))),
                ('time_acknowledged_by_successor', models.DateTimeField(default=datetime.datetime(2000, 12, 31, 23, 0, tzinfo=utc))),
                ('time_acknowledged_by_decider', models.DateTimeField(default=datetime.datetime(2000, 12, 31, 23, 0, tzinfo=utc))),
                ('predecessor_appraisal', models.IntegerField(default=0)),
                ('successor_appraisal', models.IntegerField(default=0)),
                ('decider_appraisal', models.IntegerField(default=0)),
                ('predecessor_motivation', models.TextField(blank=True, default='')),
                ('successor_motivation', models.TextField(blank=True, default='')),
                ('is_contested_by_predecessor', models.BooleanField(default=False)),
                ('is_contested_by_successor', models.BooleanField(default=False)),
                ('is_contested_by_referee', models.BooleanField(default=False)),
                ('time_instructor_assigned', models.DateTimeField(default=datetime.datetime(2000, 12, 31, 23, 0, tzinfo=utc))),
                ('appeal', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='presto.Appeal')),
                ('referee', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='presto.Referee')),
            ],
        ),
    ]