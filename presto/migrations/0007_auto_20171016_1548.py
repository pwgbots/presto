# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-10-16 13:48
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('presto', '0006_remove_appeal_appeal_motivation'),
    ]

    operations = [
        migrations.AddField(
            model_name='assignment',
            name='is_rejected',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='peerreview',
            name='assignment',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='presto.Assignment'),
        ),
    ]
