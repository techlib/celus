# Generated by Django 3.1.3 on 2021-01-13 17:17

from django.db import migrations, models
from django.db.models import Count


def fill_in_approx_count(apps, schema_editor):
    ReportType = apps.get_model('logs', 'ReportType')
    for rt in ReportType.objects.all().annotate(record_count=Count('accesslog')):
        rt.approx_record_count = rt.record_count
        rt.save()


def zero_approx_count(apps, schema_editor):
    ReportType = apps.get_model('logs', 'ReportType')
    ReportType.objects.all().update(approx_record_count=0)


class Migration(migrations.Migration):

    dependencies = [('logs', '0039_dimension_constraints')]

    operations = [
        migrations.AddField(
            model_name='reporttype',
            name='approx_record_count',
            field=models.PositiveBigIntegerField(
                default=0,
                help_text='Automatically filled in by periodic check to have some fast measure of the record count',
            ),
        ),
        migrations.RunPython(fill_in_approx_count, zero_approx_count),
    ]
