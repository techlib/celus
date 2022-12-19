# Generated by Django 2.2.4 on 2019-08-05 16:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('sushi', '0004_processing_info')]

    operations = [
        migrations.AddField(
            model_name='sushifetchattempt',
            name='queued',
            field=models.BooleanField(
                default=False,
                help_text='Was the attempt queued by the provider and should be refetched?',
            ),
        ),
        migrations.AddField(
            model_name='sushifetchattempt',
            name='when_queued',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
