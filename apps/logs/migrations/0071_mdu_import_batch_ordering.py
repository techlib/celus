# Generated by Django 3.2.15 on 2022-10-21 07:57

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [('logs', '0070_reporttype_ext_id')]

    operations = [
        migrations.AlterModelOptions(
            name='importbatch',
            options={'ordering': ('id',), 'verbose_name_plural': 'Import batches'},
        ),
        migrations.AlterModelOptions(
            name='manualdatauploadimportbatch', options={'ordering': ('mdu_id', 'import_batch_id')}
        ),
    ]
