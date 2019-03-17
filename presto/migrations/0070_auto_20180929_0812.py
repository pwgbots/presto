# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-09-29 06:12
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('presto', '0069_auto_20180921_0824'),
    ]

    operations = [
        migrations.CreateModel(
            name='ItemAssignment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('comment', models.TextField(blank=True, default='')),
                ('rating', models.IntegerField(blank=True, default=0)),
                ('assignment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='presto.Assignment')),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='presto.Item')),
            ],
        ),
        migrations.AddField(
            model_name='estafetteleg',
            name='upload_items',
            field=models.ManyToManyField(related_name='assignment_item', to='presto.Item'),
        ),
    ]
