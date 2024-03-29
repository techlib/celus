# Generated by Django 2.2.5 on 2019-09-24 11:53

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('publications', '0012_platform_source'),
        ('organizations', '0012_timestamps'),
        ('logs', '0024_no_reportinterestmetric_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='Annotation',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('subject', models.CharField(max_length=200)),
                ('subject_en', models.CharField(max_length=200, null=True)),
                ('subject_cs', models.CharField(max_length=200, null=True)),
                ('short_message', models.TextField(blank=True)),
                ('short_message_en', models.TextField(blank=True, null=True)),
                ('short_message_cs', models.TextField(blank=True, null=True)),
                ('message', models.TextField(blank=True)),
                ('message_en', models.TextField(blank=True, null=True)),
                ('message_cs', models.TextField(blank=True, null=True)),
                ('start_date', models.DateField(blank=True, null=True)),
                ('end_date', models.DateField(blank=True, null=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                (
                    'author',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'organization',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to='organizations.Organization',
                    ),
                ),
                (
                    'platform',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to='publications.Platform',
                    ),
                ),
                (
                    'report_type',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to='logs.ReportType',
                    ),
                ),
                (
                    'title',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to='publications.Title',
                    ),
                ),
            ],
        )
    ]
