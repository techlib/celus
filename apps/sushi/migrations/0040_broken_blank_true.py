# Generated by Django 3.1.6 on 2021-03-29 07:58

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('sushi', '0039_remove_http_auth_from_c5')]

    operations = [
        migrations.AlterModelOptions(
            name='counterreportstocredentials',
            options={'verbose_name_plural': 'Counter reports to credentials'},
        ),
        migrations.AlterField(
            model_name='counterreportstocredentials',
            name='broken',
            field=models.CharField(
                blank=True,
                choices=[('http', 'HTTP'), ('sushi', 'SUSHI')],
                help_text='Indication that credentails are broken',
                max_length=20,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='counterreportstocredentials',
            name='first_broken_attempt',
            field=models.OneToOneField(
                blank=True,
                help_text='Which was the first broken attempt',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='sushi.sushifetchattempt',
            ),
        ),
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
                    ('MR1', 'MR1'),
                    ('TR', 'TR'),
                    ('PR', 'PR'),
                    ('DR', 'DR'),
                    ('IR', 'IR'),
                ],
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name='sushicredentials',
            name='broken',
            field=models.CharField(
                blank=True,
                choices=[('http', 'HTTP'), ('sushi', 'SUSHI')],
                help_text='Indication that credentails are broken',
                max_length=20,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='sushicredentials',
            name='first_broken_attempt',
            field=models.OneToOneField(
                blank=True,
                help_text='Which was the first broken attempt',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='sushi.sushifetchattempt',
            ),
        ),
    ]
