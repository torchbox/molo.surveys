# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2017-10-18 16:18
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('surveys', '0016_merge'),
    ]

    operations = [
        migrations.AlterField(
            model_name='articletagrule',
            name='tag',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.Tag'),
        ),
    ]