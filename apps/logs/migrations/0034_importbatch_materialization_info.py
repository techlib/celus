# Generated by Django 2.2.10 on 2020-05-15 12:09

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('logs', '0033_add_reportmaterializationspec'),
    ]

    operations = [
        migrations.AddField(
            model_name='importbatch',
            name='materialization_data',
            field=django.contrib.postgres.fields.jsonb.JSONField(
                default=dict,
                blank=True,
                help_text='Internal information about materialized report data in this batch',
            ),
        ),
        migrations.AlterField(
            model_name='reportmaterializationspec',
            name='base_report_type',
            field=models.ForeignKey(
                limit_choices_to={'materialization_spec__isnull': True},
                on_delete=django.db.models.deletion.CASCADE,
                to='logs.ReportType',
            ),
        ),
    ]