# Generated by Django 3.2.15 on 2022-10-26 13:09

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [('logs', '0072_nibbler')]

    operations = [
        migrations.AlterUniqueTogether(
            name='reportinterestmetric',
            unique_together={('interest_group', 'metric', 'report_type')},
        )
    ]
