# Generated by Django 2.2.16 on 2020-10-30 09:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('scheduler', '0005_fetchintention_date_constraint')]

    operations = [
        migrations.AddField(
            model_name='fetchintention',
            name='retry_id',
            field=models.IntegerField(blank=True, help_text='Identifier of retry queue', null=True),
        )
    ]
