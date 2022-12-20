# Generated by Django 3.1.8 on 2021-09-06 20:49

import django.core.validators
import django.db.models.deletion
import knowledgebase.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_unique_name_within_organization_data_source'),
        ('knowledgebase', '0002_jsonfield'),
    ]

    operations = [
        migrations.CreateModel(
            name='RouterSyncAttempt',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                (
                    'prefix',
                    models.CharField(
                        max_length=8, validators=[django.core.validators.MinLengthValidator(8)]
                    ),
                ),
                (
                    'target',
                    models.CharField(
                        choices=[('A', 'absent'), ('P', 'present')], default='P', max_length=1
                    ),
                ),
                ('retries', models.PositiveIntegerField(default=0)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('done', models.DateTimeField(blank=True, null=True)),
                ('last_error', models.TextField(blank=True, null=True)),
                (
                    'source',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to='core.datasource'
                    ),
                ),
            ],
            bases=(knowledgebase.models.AuthTokenMixin, models.Model),
        )
    ]
