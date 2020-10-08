# Generated by Django 2.2.14 on 2020-08-12 17:34

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_user_extra_data'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='extra_data',
            field=django.contrib.postgres.fields.jsonb.JSONField(
                blank=True,
                default=dict,
                help_text='User state data that do not deserve a dedicated field',
            ),
        ),
    ]