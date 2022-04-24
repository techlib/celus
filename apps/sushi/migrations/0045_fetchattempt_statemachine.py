# Generated by Django 3.1.8 on 2021-07-30 13:06

from django.db import migrations, models


def bools_to_state(apps, schema_editor):
    SushiFetchAttempt = apps.get_model('sushi', 'SushiFetchAttempt')
    for attempt in SushiFetchAttempt.objects.all().iterator():
        if attempt.import_crashed:
            attempt.status = "import_failed"
        elif attempt.in_progress:
            attempt.status = "downloading"
        elif attempt.contains_data:
            attempt.status = "success"
        elif not attempt.download_success:
            attempt.status = "download_failed"
        elif not attempt.processing_success:
            attempt.status = "parsing_failed"
        elif attempt.is_processed:
            attempt.status = "no_data"
        else:
            # the error_code and import_batch are the only things we can use
            if attempt.error_code in ('3030', '3031'):
                attempt.status = "no_data"
            elif attempt.import_batch:
                attempt.status = "success"
            else:
                attempt.status = "download_failed"

        attempt.save()


class Migration(migrations.Migration):

    dependencies = [
        ('sushi', '0044_fix_data_already_imported'),
    ]

    operations = [
        migrations.AddField(
            model_name='sushifetchattempt',
            name='status',
            field=models.CharField(
                choices=[
                    ('initial', 'Initial'),
                    ('downloading', 'Downloading'),
                    ('imported', 'Importing'),
                    ('success', 'Success'),
                    ('unprocessed', 'Unprocessed'),
                    ('no_data', 'No data'),
                    ('import_failed', 'Import failed'),
                    ('parsing_failed', 'Parsing failed'),
                    ('download_failed', 'Download failed'),
                    ('credentails_broken', 'Broken credentials'),
                    ('canceled', 'Canceled'),
                ],
                default='initial',
                max_length=20,
            ),
        ),
        migrations.RunPython(bools_to_state, migrations.RunPython.noop),
        migrations.RemoveField(model_name='sushifetchattempt', name='contains_data',),
        migrations.RemoveField(model_name='sushifetchattempt', name='download_success',),
        migrations.RemoveField(model_name='sushifetchattempt', name='import_crashed',),
        migrations.RemoveField(model_name='sushifetchattempt', name='in_progress',),
        migrations.RemoveField(model_name='sushifetchattempt', name='is_processed',),
        migrations.RemoveField(model_name='sushifetchattempt', name='processing_success',),
        migrations.RemoveField(model_name='sushifetchattempt', name='queued',),
    ]
