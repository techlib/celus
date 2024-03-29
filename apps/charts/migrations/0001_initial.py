# Generated by Django 2.2.5 on 2019-09-09 08:47

import django.contrib.postgres.fields.jsonb
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [('core', '0007_timestamps'), ('logs', '0022_move_some_models_to_charts')]

    operations = [
        migrations.CreateModel(
            name='ReportDataView',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('short_name', models.CharField(max_length=100)),
                ('name', models.CharField(max_length=250)),
                ('name_en', models.CharField(max_length=250, null=True)),
                ('name_cs', models.CharField(max_length=250, null=True)),
                ('desc', models.TextField(blank=True)),
                ('desc_en', models.TextField(blank=True, null=True)),
                ('desc_cs', models.TextField(blank=True, null=True)),
                (
                    'metric_allowed_values',
                    django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=list),
                ),
                (
                    'base_report_type',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to='logs.ReportType'
                    ),
                ),
                (
                    'primary_dimension',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to='logs.Dimension',
                    ),
                ),
                (
                    'source',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to='core.DataSource',
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name='DimensionFilter',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                (
                    'allowed_values',
                    django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=list),
                ),
                (
                    'dimension',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to='logs.Dimension'
                    ),
                ),
                (
                    'report_data_view',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='dimension_filters',
                        to='charts.ReportDataView',
                    ),
                ),
            ],
        ),
    ]
