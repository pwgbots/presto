# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-09-20 14:19
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('presto', '0067_courseestafette_time_chart_update'),
    ]

    operations = [
        migrations.AlterField(
            model_name='courseestafette',
            name='chart',
            field=models.ImageField(blank=True, default=None, null=True, upload_to='charts'),
        ),
    ]
