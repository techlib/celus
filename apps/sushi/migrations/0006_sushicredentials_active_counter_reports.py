# Generated by Django 2.2.1 on 2019-08-08 15:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('sushi', '0005_attemp_queuing')]

    operations = [
        migrations.AddField(
            model_name='sushicredentials',
            name='active_counter_reports',
            field=models.ManyToManyField(to='sushi.CounterReportType'),
        )
    ]
