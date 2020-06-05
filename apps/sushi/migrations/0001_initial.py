# Generated by Django 2.2.1 on 2019-08-02 10:41

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('logs', '0004_source_field'),
        ('publications', '0005_auto_20190801_1615'),
        ('organizations', '0010_delete_sushicredentials'),
    ]

    operations = [
        migrations.CreateModel(
            name='SushiCredentials',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('url', models.URLField()),
                (
                    'counter_version',
                    models.PositiveSmallIntegerField(choices=[(4, 'COUNTER 4'), (5, 'COUNTER 5')]),
                ),
                ('requestor_id', models.CharField(max_length=128)),
                ('customer_id', models.CharField(blank=True, max_length=128)),
                ('http_username', models.CharField(blank=True, max_length=128)),
                ('http_password', models.CharField(blank=True, max_length=128)),
                ('api_key', models.CharField(blank=True, max_length=128)),
                (
                    'extra_params',
                    django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict),
                ),
                ('enabled', models.BooleanField(default=True)),
                (
                    'organization',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to='organizations.Organization'
                    ),
                ),
                (
                    'platform',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to='publications.Platform'
                    ),
                ),
            ],
            options={
                'verbose_name_plural': 'Sushi credentials',
                'unique_together': {('organization', 'platform', 'counter_version')},
            },
        ),
        migrations.CreateModel(
            name='CounterReportType',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('code', models.CharField(max_length=20)),
                ('name', models.CharField(blank=True, max_length=128)),
                (
                    'counter_version',
                    models.PositiveSmallIntegerField(choices=[(4, 'COUNTER 4'), (5, 'COUNTER 5')]),
                ),
                (
                    'report_type',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to='logs.ReportType'
                    ),
                ),
            ],
            options={
                'verbose_name_plural': 'COUNTER report type',
                'unique_together': {('code', 'counter_version')},
            },
        ),
    ]
