# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2022-11-15 20:21
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0032_auto_20220811_2056'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentinfo',
            name='pronoun',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='teacherinfo',
            name='pronoun',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]