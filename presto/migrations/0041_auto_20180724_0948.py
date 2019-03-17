# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-07-24 07:48
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('presto', '0040_auto_20180723_1736'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='appraisaloption',
            options={'ordering': ['value']},
        ),
        migrations.AddField(
            model_name='appraisaloption',
            name='icon',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
        migrations.AddField(
            model_name='itemappraisal',
            name='icon',
            field=models.CharField(default='sort numeric down', max_length=64),
        ),
        migrations.AlterField(
            model_name='appraisaloption',
            name='label',
            field=models.CharField(max_length=64),
        ),
        migrations.AlterField(
            model_name='itemappraisal',
            name='style',
            field=models.CharField(max_length=32),
        ),
    ]
