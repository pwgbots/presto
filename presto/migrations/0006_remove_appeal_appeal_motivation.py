# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-10-03 05:15
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('presto', '0005_auto_20171002_2206'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='appeal',
            name='appeal_motivation',
        ),
    ]
