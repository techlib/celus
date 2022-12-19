# Generated by Django 2.2.4 on 2019-08-24 15:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('logs', '0013_nullable_title_mdu_validation')]

    operations = [
        migrations.AlterField(
            model_name='dimension',
            name='type',
            field=models.PositiveSmallIntegerField(
                choices=[(1, 'integer'), (2, 'text')], default=2
            ),
        )
    ]
