# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-09-12 20:34
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('presto', '0061_auto_20180912_1227'),
    ]

    operations = [
        migrations.AddField(
            model_name='referee',
            name='passed_exam',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='presto.RefereeExam'),
        ),
        migrations.AlterField(
            model_name='letterofacknowledgement',
            name='referee',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='presto.Referee'),
        ),
    ]
