# Generated by Django 3.2.16 on 2022-11-23 13:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('organizations', '0021_alter_organization_options')]

    operations = [
        migrations.AddField(
            model_name='organization',
            name='raw_data_import_enabled',
            field=models.BooleanField(default=False),
        )
    ]
