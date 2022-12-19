# Generated by Django 2.2.4 on 2019-08-16 07:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('logs', '0008_importbatch'),
        ('sushi', '0006_sushicredentials_active_counter_reports'),
    ]

    operations = [
        migrations.AddField(
            model_name='sushifetchattempt',
            name='import_batch',
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.SET_NULL, to='logs.ImportBatch'
            ),
        )
    ]
