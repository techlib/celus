# Generated by Django 3.1.3 on 2020-11-20 13:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('core', '0012_datasource_set_null')]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='extra_data',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='User state data that do not deserve a dedicated field',
            ),
        )
    ]
