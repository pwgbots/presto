# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-03-24 12:19
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('presto', '0033_auto_20180324_1042'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='is_edX',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='coursestudent',
            name='has_passed',
            field=models.BooleanField(default=False),
        ),
    ]
