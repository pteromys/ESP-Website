# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2024-02-20 21:24
from __future__ import unicode_literals

from django.conf import settings
from django.core import validators
from django.db import migrations, models
import django.db.models.fields
import re

def replace_director_emails(apps, schema_editor):
    Program = apps.get_model('program', 'Program')
    for prog in Program.objects.all():
        if not re.match(r'(^.+@{0}$)|(^.+@(\w+\.)?learningu\.org$)'.format(settings.SITE_INFO[1].replace('.', '\.')), prog.director_email):
            prog.director_email = 'info@' + settings.SITE_INFO[1]
            prog.save()

def create_info_redirect(apps, schema_editor):
    PlainRedirect = apps.get_model('dbmail', 'PlainRedirect')
    prs = PlainRedirect.objects.filter(original = "info")
    if not prs.exists():
        redirect = PlainRedirect.objects.create(original = "info", destination = settings.DEFAULT_EMAIL_ADDRESSES['default'])

class Migration(migrations.Migration):

    dependencies = [
        ('program', '0026_auto_20221122_2100'),
    ]

    operations = [
        migrations.AlterField(
            model_name='program',
            name='director_email',
            field=models.EmailField(default=b'info@' + settings.SITE_INFO[1], max_length=75,
                                    help_text=b'The director email address must end in @' + settings.SITE_INFO[1] +
                                              ' (your website), @learningu.org, or a valid subdomain of learningu.org (i.e., @subdomain.learningu.org). The default is <b>info@' + settings.SITE_INFO[1] +
                                              '</b>, which redirects to the "default" email address from your site\'s settings by default. You can create and manage your email redirects <a href="/manage/redirects/">here</a>.',
                                    validators=[validators.RegexValidator(r'(^.+@{0}$)|(^.+<.+@{0}>$)|(^.+@(\w+\.)?learningu\.org$)|(^.+<.+@(\w+\.)?learningu\.org>$)'.format(settings.SITE_INFO[1].replace('.', '\.')))]),
        ),
        # This will run backwards, but won't do anything
        migrations.RunPython(replace_director_emails, lambda a, s: None),
        migrations.RunPython(create_info_redirect, lambda a, s: None),
    ]
