# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2024-02-08 20:52
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations
import django.db.models.deletion
import esp.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0034_auto_20230525_2024'),
        ('dbmail', '0005_auto_20220719_2056'),
    ]

    operations = [
        migrations.AddField(
            model_name='textofemail',
            name='user',
            field=esp.db.fields.AjaxForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='users.ESPUser'),
        ),
    ]
