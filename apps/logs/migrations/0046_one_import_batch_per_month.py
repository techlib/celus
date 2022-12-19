# Generated by Django 3.2.7 on 2021-09-24 12:29

from django.db import migrations

from logs.logic.split_fetch_intentions import split_fetch_intentions


def split_import_batches(apps, schema_editor):
    fetchintention_model = apps.get_model('scheduler', 'FetchIntention')
    accesslog_model = apps.get_model('logs', 'AccessLog')
    split_fetch_intentions(accesslog_model, fetchintention_model)


class Migration(migrations.Migration):

    dependencies = [
        ('logs', '0045_dimension_int_to_str'),
        ('scheduler', '0012_fill_queue_id'),
        ('sushi', '0046_fetchintentions_for_fetch_attempts'),
    ]

    operations = [migrations.RunPython(split_import_batches, migrations.RunPython.noop)]
