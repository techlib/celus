# Generated by Django 2.2.5 on 2019-09-20 07:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('sushi', '0019_add_defaults_to_sushifetchattempt_booleans')]

    operations = [
        migrations.AlterField(
            model_name='counterreporttype',
            name='code',
            field=models.CharField(
                choices=[
                    ('JR1', 'JR1'),
                    ('JR1a', 'JR1a'),
                    ('JR1GOA', 'JR1GOA'),
                    ('JR2', 'JR2'),
                    ('BR1', 'BR1'),
                    ('BR2', 'BR2'),
                    ('BR3', 'BR3'),
                    ('DB1', 'DB1'),
                    ('DB2', 'DB2'),
                    ('PR1', 'PR1'),
                    ('TR', 'TR'),
                    ('PR', 'PR'),
                    ('DR', 'DR'),
                ],
                max_length=10,
            ),
        )
    ]
