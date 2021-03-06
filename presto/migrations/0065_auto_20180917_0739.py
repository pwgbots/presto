# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-09-17 05:39
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('presto', '0064_auto_20180916_1656'),
    ]

    operations = [
        migrations.AddField(
            model_name='peerreview',
            name='is_offensive',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterUniqueTogether(
            name='prestobadge',
            unique_together=set([('course', 'participant', 'referee', 'attained_level')]),
        ),
    ]
