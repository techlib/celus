# Generated by Django 2.2.4 on 2019-09-02 07:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('logs', '0016_report_interest_metrics'),
        ('publications', '0009_even_more_pub_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='platform',
            name='interest_reports',
            field=models.ManyToManyField(to='logs.ReportType'),
        )
    ]
