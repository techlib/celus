# Generated by Django 2.2.4 on 2019-08-28 07:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('sushi', '0010_counterreporttype_code_choices')]

    operations = [
        migrations.AddField(
            model_name='sushifetchattempt',
            name='error_code',
            field=models.CharField(blank=True, max_length=12),
        )
    ]
