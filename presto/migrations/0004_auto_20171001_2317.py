# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-10-01 21:17
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('presto', '0003_auto_20170930_1045'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appeal',
            name='appeal_type',
            field=models.IntegerField(blank=True, default=0),
        ),
    ]
