# Generated by Django 3.2.13 on 2022-06-02 10:58

import core.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sushi', '0052_select_best_empty_importbatch'),
    ]

    operations = [
        migrations.AddField(
            model_name='sushifetchattempt',
            name='checksum',
            field=models.CharField(default='', max_length=128),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='sushifetchattempt',
            name='file_size',
            field=models.PositiveIntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='sushifetchattempt',
            name='data_file',
            field=models.FileField(
                blank=True, max_length=256, null=True, upload_to=core.models.where_to_store
            ),
        ),
    ]
