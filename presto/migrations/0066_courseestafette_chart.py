# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-09-20 12:56
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('presto', '0065_auto_20180917_0739'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseestafette',
            name='chart',
            field=models.ImageField(blank=True, default=None, null=True, upload_to=b'C:\\Users\\Pieter Bots\\Documents\\PrESTO\\git\\static\\presto\\charts'),
        ),
    ]