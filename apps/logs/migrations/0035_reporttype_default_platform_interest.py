# Generated by Django 2.2.15 on 2020-09-25 13:05

from django.db import migrations, models


def set_default_platform_interest(apps, schema_editor):
    ReportType = apps.get_model('logs', 'ReportType')
    ReportType.objects.filter(short_name__in=('TR', 'DR', 'JR1', 'BR2', 'DB1')).update(
        default_platform_interest=True
    )


class Migration(migrations.Migration):

    dependencies = [('logs', '0034_importbatch_materialization_info')]

    operations = [
        migrations.AddField(
            model_name='reporttype',
            name='default_platform_interest',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(set_default_platform_interest, migrations.RunPython.noop),
    ]
