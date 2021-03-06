# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-07-24 09:30
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('presto', '0041_auto_20180724_0948'),
    ]

    operations = [
        migrations.CreateModel(
            name='ItemReview',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('comment', models.TextField(blank=True, default='')),
                ('rating', models.IntegerField(blank=True, default=0)),
            ],
        ),
        migrations.AddField(
            model_name='item',
            name='no_comment',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='itemappraisal',
            name='style',
            field=models.CharField(max_length=64),
        ),
        migrations.AddField(
            model_name='itemreview',
            name='item',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='presto.Item'),
        ),
        migrations.AddField(
            model_name='itemreview',
            name='review',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='presto.PeerReview'),
        ),
    ]
