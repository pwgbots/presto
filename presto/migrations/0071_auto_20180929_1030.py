# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-09-29 08:30
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('presto', '0070_auto_20180929_0812'),
    ]

    operations = [
        migrations.AlterField(
            model_name='estafetteleg',
            name='required_files',
            field=models.CharField(blank=True, default='', max_length=256),
        ),
    ]