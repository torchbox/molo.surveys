# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2017-08-11 14:23
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('surveys', '0008_submission_article_yourwords_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='molosurveypage',
            name='homepage_button_text',
            field=models.TextField(blank=True),
        ),
    ]