# Generated by Django 3.2.10 on 2022-02-02 14:04

from django.db import migrations, models


def convert_broken_credentials_state(apps, schema_editor):
    SushiFetchAttempt = apps.get_model('sushi', 'SushiFetchAttempt')
    SushiFetchAttempt.objects.filter(status="credentails_broken").update(status="download_failed")


class Migration(migrations.Migration):

    dependencies = [
        ('sushi', '0047_no_data_for_3031_and_3030'),
    ]

    operations = [
        migrations.RunPython(convert_broken_credentials_state, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='sushifetchattempt',
            name='status',
            field=models.CharField(
                choices=[
                    ('initial', 'Initial'),
                    ('downloading', 'Downloading'),
                    ('importing', 'Importing'),
                    ('success', 'Success'),
                    ('unprocessed', 'Unprocessed'),
                    ('no_data', 'No data'),
                    ('import_failed', 'Import failed'),
                    ('parsing_failed', 'Parsing failed'),
                    ('download_failed', 'Download failed'),
                    ('canceled', 'Canceled'),
                ],
                default='initial',
                max_length=20,
            ),
        ),
    ]