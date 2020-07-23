# Generated by Django 2.2.13 on 2020-06-25 13:53

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0015_nullable_ext_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='organization',
            name='address',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict),
        ),
        migrations.AlterField(
            model_name='organization',
            name='ext_id',
            field=models.PositiveIntegerField(
                blank=True,
                default=None,
                help_text='object ID taken from EMRS',
                null=True,
                unique=True,
            ),
        ),
        migrations.AlterField(
            model_name='organization',
            name='internal_id',
            field=models.CharField(
                blank=True,
                help_text='special ID used for internal purposes',
                max_length=50,
                null=True,
                unique=True,
            ),
        ),
    ]