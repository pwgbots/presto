# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-12-02 21:49
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('presto', '0015_peerreview_final_review_index'),
    ]

    operations = [
        migrations.AddField(
            model_name='estafettecase',
            name='required_keywords',
            field=models.CharField(blank=True, max_length=512),
        ),
        migrations.AddField(
            model_name='estafetteleg',
            name='required_keywords',
            field=models.CharField(blank=True, max_length=512),
        ),
    ]
