# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-02-28 13:44
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('presto', '0026_usersession_session_key'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseestafette',
            name='bonus_per_step',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='courseestafette',
            name='speed_bonus',
            field=models.FloatField(default=0),
        ),
    ]