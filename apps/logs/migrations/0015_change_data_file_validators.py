# Generated by Django 2.2.4 on 2019-08-29 07:37

from django.db import migrations, models
import logs.models


class Migration(migrations.Migration):

    dependencies = [('logs', '0014_default_dimension_type')]

    operations = [
        migrations.AlterField(
            model_name='manualdataupload',
            name='data_file',
            field=models.FileField(
                upload_to=logs.models.where_to_store, validators=[logs.models.validate_mime_type]
            ),
        )
    ]
