# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2024-11-21 21:56
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('survey', '0003_auto_20240509_2341'),
    ]

    operations = [
        migrations.AddField(
            model_name='answer',
            name='value_type',
            field=models.TextField(default='str'),
            preserve_default=False,
        ),
    ]
