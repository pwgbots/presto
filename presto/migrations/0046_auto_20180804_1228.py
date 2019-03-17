# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-08-04 10:28
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('presto', '0045_auto_20180803_0819'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseestafette',
            name='high_grade_range',
            field=models.IntegerField(default=10),
        ),
        migrations.AddField(
            model_name='courseestafette',
            name='high_score_range',
            field=models.IntegerField(default=1000),
        ),
        migrations.AddField(
            model_name='courseestafette',
            name='low_grade_range',
            field=models.IntegerField(default=1),
        ),
        migrations.AddField(
            model_name='courseestafette',
            name='low_score_range',
            field=models.IntegerField(default=-1000),
        ),
        migrations.AddField(
            model_name='courseestafette',
            name='passing_grade',
            field=models.FloatField(default=5.5),
        ),
    ]
