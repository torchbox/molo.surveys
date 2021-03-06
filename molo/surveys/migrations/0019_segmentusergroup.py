# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2017-10-26 17:56
from __future__ import unicode_literals

import django
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('surveys', '0018_add_combination_rule'),
    ]

    operations = [
        migrations.CreateModel(
            name='SegmentUserGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=254)),
                ('users', models.ManyToManyField(related_name='segment_groups', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AlterField(
            model_name='groupmembershiprule',
            name='group',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='surveys.SegmentUserGroup'),
        ),
    ]
