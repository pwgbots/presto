# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-11-21 12:05
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('presto', '0010_auto_20171121_1217'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='userdownload',
            options={'ordering': ['time_downloaded']},
        ),
    ]
