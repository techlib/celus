# Generated by Django 3.2.12 on 2022-04-11 07:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('sushi', '0049_sushifetchattempt_extracted_data')]

    operations = [
        migrations.AlterField(
            model_name='sushicredentials',
            name='api_key',
            field=models.CharField(blank=True, max_length=400),
        )
    ]
