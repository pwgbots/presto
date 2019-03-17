# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-03-22 15:20
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('presto', '0028_auto_20180322_1502'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='letterofaknowledgement',
            name='course',
        ),
        migrations.AddField(
            model_name='letterofaknowledgement',
            name='estafette',
            field=models.ForeignKey(default=0, on_delete=django.db.models.deletion.PROTECT, to='presto.CourseEstafette'),
            preserve_default=False,
        ),
    ]
