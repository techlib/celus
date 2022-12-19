# Generated by Django 2.2.1 on 2019-08-06 14:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('logs', '0004_source_field')]

    operations = [
        migrations.AddField(
            model_name='metric',
            name='active',
            field=models.BooleanField(
                default=True, help_text='Only active metrics are reported to users'
            ),
        )
    ]
