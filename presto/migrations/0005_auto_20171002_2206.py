# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-10-02 20:06
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('presto', '0004_auto_20171001_2317'),
    ]

    operations = [
        migrations.RenameField(
            model_name='appeal',
            old_name='verdict',
            new_name='grade',
        ),
        migrations.RenameField(
            model_name='appeal',
            old_name='verdict_motivation',
            new_name='grade_motivation',
        ),
    ]