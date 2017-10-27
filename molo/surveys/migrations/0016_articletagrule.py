# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2017-10-12 13:16
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import modelcluster.fields


class Migration(migrations.Migration):

    dependencies = [
        ('taggit', '0002_auto_20150616_2121'),
        ('wagtail_personalisation', '0012_remove_personalisablepagemetadata_is_segmented'),
        ('surveys', '0015_add_choices_to_skip_logic'),
    ]

    operations = [
        migrations.CreateModel(
            name='ArticleTagRule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('operator', models.CharField(choices=[(b'gt', 'more than'), (b'lt', 'less than'), (b'eq', 'equal to')], default=b'gt', max_length=3, verbose_name='operator')),
                ('count', models.IntegerField()),
                ('date_from', models.DateTimeField(null=True, blank=True)),
                ('date_to', models.DateTimeField(null=True, blank=True, help_text=b'All times are UTC. Leave both fields blank to search for all time.')),
                ('segment', modelcluster.fields.ParentalKey(on_delete=django.db.models.deletion.CASCADE, related_name='surveys_articletagrule_related', related_query_name='%(app_label)s_%(class)ss', to='wagtail_personalisation.Segment')),
                ('tag', models.ForeignKey(help_text='The number in the bracket indicates the number of articles that have the tag.', on_delete=django.db.models.deletion.CASCADE, to='core.Tag')),
            ],
            options={
                'verbose_name': 'Article tag rule',
            },
        ),
    ]