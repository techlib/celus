# Generated by Django 3.2.15 on 2022-12-01 14:12

from django.core.exceptions import ObjectDoesNotExist
from django.db import migrations, models


def derive_method(apps, schema_editor):
    ManualDataUpload = apps.get_model('logs', 'ManualDataUpload')
    for mdu in ManualDataUpload.objects.all():
        if mdu.use_nibbler:
            mdu.method = "raw"
        else:
            try:
                mdu.report_type.counterreporttype
                mdu.method = "counter"
            except ObjectDoesNotExist:
                mdu.method = "celus"

        mdu.save()


def derive_use_nibbler(apps, schema_editor):
    ManualDataUpload = apps.get_model('logs', 'ManualDataUpload')
    for mdu in ManualDataUpload.objects.all():
        if mdu.method == "raw":
            mdu.use_nibbler = True
        else:
            mdu.use_nibbler = False
        mdu.save()


class Migration(migrations.Migration):

    dependencies = [
        ('logs', '0073_alter_reportinterestmetric_unique_together'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='manualdataupload', name='non-nibbler-needs-report-type',
        ),
        migrations.AddField(
            model_name='manualdataupload',
            name='method',
            field=models.CharField(
                choices=[
                    ('counter', 'Counter format'),
                    ('celus', 'Celus format'),
                    ('raw', 'Raw data'),
                ],
                default='counter',
                max_length=20,
            ),
        ),
        migrations.RunPython(derive_method, derive_use_nibbler),
        migrations.RemoveField(model_name='manualdataupload', name='use_nibbler',),
        migrations.AddConstraint(
            model_name='manualdataupload',
            constraint=models.CheckConstraint(
                check=models.Q(
                    ('method__in', ['counter', 'celus']),
                    ('report_type__isnull', True),
                    _negated=True,
                ),
                name='non-raw-needs-report-type',
            ),
        ),
    ]
