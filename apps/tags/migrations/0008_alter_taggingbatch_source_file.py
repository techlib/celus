# Generated by Django 3.2.16 on 2022-12-09 13:49

from django.db import migrations, models
import tags.models


class Migration(migrations.Migration):

    dependencies = [
        ('tags', '0007_tagging_batch_internal_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='taggingbatch',
            name='source_file',
            field=models.FileField(
                blank=True,
                max_length=256,
                null=True,
                upload_to=tags.models.where_to_store,
                validators=[tags.models.validate_mime_type],
            ),
        ),
    ]
