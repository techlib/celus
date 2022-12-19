# Generated by Django 2.2.5 on 2019-10-02 14:36

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [('sushi', '0021_sushifetchattempt_import_crashed')]

    operations = [
        migrations.AddField(
            model_name='sushicredentials',
            name='created',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='sushicredentials',
            name='last_updated',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='sushicredentials',
            name='lock_level',
            field=models.PositiveSmallIntegerField(
                choices=[
                    (0, 'Unlocked'),
                    (300, 'Organization admin'),
                    (400, 'Consortium staff'),
                    (1000, 'Superuser'),
                ],
                default=0,
                help_text='Only user with the same or higher level can unlock it and/or edit it',
            ),
        ),
        migrations.AddField(
            model_name='sushicredentials',
            name='outside_consortium',
            field=models.BooleanField(
                default=False,
                help_text='True if these credentials belong to access bought outside of the consortium - necessary for proper cost calculation',
            ),
        ),
    ]
