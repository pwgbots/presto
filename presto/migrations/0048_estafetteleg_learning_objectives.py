# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-08-10 08:21
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('presto', '0047_auto_20180804_1608'),
    ]

    operations = [
        migrations.AddField(
            model_name='estafetteleg',
            name='learning_objectives',
            field=models.TextField(blank=True, default=''),
        ),
    ]
