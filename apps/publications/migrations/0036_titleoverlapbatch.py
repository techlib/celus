# Generated by Django 3.2.18 on 2023-02-28 12:04

import django.db.models.deletion
import django.utils.timezone
import publications.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('organizations', '0022_organization_raw_enabled'),
        ('publications', '0035_alter_platform_source'),
    ]

    operations = [
        migrations.CreateModel(
            name='TitleOverlapBatch',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                (
                    'source_file',
                    models.FileField(
                        blank=True,
                        max_length=256,
                        null=True,
                        upload_to=publications.models.where_to_store,
                        validators=[publications.models.validate_mime_type],
                    ),
                ),
                (
                    'annotated_file',
                    models.FileField(
                        blank=True,
                        help_text='File with additional data added during processing',
                        max_length=256,
                        null=True,
                        upload_to='overlap_batch/',
                    ),
                ),
                (
                    'processing_info',
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text='Information gathered during processing of the source file',
                    ),
                ),
                (
                    'state',
                    models.CharField(
                        choices=[
                            ('initial', 'Initial'),
                            ('processing', 'Processing'),
                            ('failed', 'Import failed'),
                            ('done', 'Done'),
                        ],
                        default='initial',
                        max_length=20,
                    ),
                ),
                (
                    'last_updated_by',
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'organization',
                    models.ForeignKey(
                        blank=True,
                        help_text='Titles will only be looked up for this organization',
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to='organizations.organization',
                    ),
                ),
            ],
            options={'verbose_name_plural': 'Title overlap batches'},
        )
    ]
