# Generated by Django 2.2.5 on 2019-09-20 14:09

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('logs', '0023_importbatch_interest_processed'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='reportinterestmetric',
            name='name',
        ),
        migrations.RemoveField(
            model_name='reportinterestmetric',
            name='name_cs',
        ),
        migrations.RemoveField(
            model_name='reportinterestmetric',
            name='name_en',
        ),
    ]
