# Generated by Django 3.2.13 on 2022-06-02 13:40

import core.models
import logs.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('logs', '0066_lastaction')]

    operations = [
        migrations.AddField(
            model_name='manualdataupload',
            name='checksum',
            field=models.CharField(default='', max_length=128),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='manualdataupload',
            name='file_size',
            field=models.PositiveIntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='manualdataupload',
            name='data_file',
            field=models.FileField(
                blank=True,
                max_length=256,
                null=True,
                upload_to=core.models.where_to_store,
                validators=[logs.models.validate_mime_type],
            ),
        ),
    ]
