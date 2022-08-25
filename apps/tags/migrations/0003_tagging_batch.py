# Generated by Django 3.2.15 on 2022-08-29 14:49

import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

import tags.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tags', '0002_tagclass_defaults_for_tag'),
    ]

    operations = [
        migrations.CreateModel(
            name='TaggingBatch',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                (
                    'source_file',
                    models.FileField(
                        blank=True, max_length=256, null=True, upload_to=tags.models.where_to_store
                    ),
                ),
                (
                    'annotated_file',
                    models.FileField(
                        blank=True,
                        help_text='File with additional data added during pre-flight or import',
                        max_length=256,
                        null=True,
                        upload_to='tagging_batch/',
                    ),
                ),
                (
                    'preflight',
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text='Information gathered during the preflight check of the source',
                    ),
                ),
                (
                    'postflight',
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text='Information gathered during the actual processing of the source and application of tags',
                    ),
                ),
                (
                    'state',
                    models.CharField(
                        choices=[
                            ('initial', 'Initial'),
                            ('preflight', 'Preflight'),
                            ('importing', 'Importing'),
                            ('imported', 'Imported'),
                            ('prefailed', 'Preflight failed'),
                            ('failed', 'Import failed'),
                            ('undoing', 'Undoing'),
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
                    'tag',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to='tags.tag',
                    ),
                ),
                (
                    'tag_class',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to='tags.tagclass',
                    ),
                ),
            ],
            options={'verbose_name_plural': 'Tagging batches',},
        ),
        migrations.AddField(
            model_name='organizationtag',
            name='tagging_batch',
            field=models.ForeignKey(
                blank=True,
                help_text='If the tagging was done in a batch, this is the batch',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='tags.taggingbatch',
            ),
        ),
        migrations.AddField(
            model_name='platformtag',
            name='tagging_batch',
            field=models.ForeignKey(
                blank=True,
                help_text='If the tagging was done in a batch, this is the batch',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='tags.taggingbatch',
            ),
        ),
        migrations.AddField(
            model_name='titletag',
            name='tagging_batch',
            field=models.ForeignKey(
                blank=True,
                help_text='If the tagging was done in a batch, this is the batch',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='tags.taggingbatch',
            ),
        ),
        migrations.AddConstraint(
            model_name='taggingbatch',
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(('state__in', ['imported', 'importing', 'failed']), _negated=True),
                    models.Q(('tag__isnull', True), ('tag_class__isnull', False)),
                    models.Q(('tag__isnull', False), ('tag_class__isnull', True)),
                    _connector='OR',
                ),
                name='one_of_tag_and_tag_class_not_null',
            ),
        ),
    ]
