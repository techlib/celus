# Generated by Django 2.2.9 on 2019-12-23 09:22

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [('logs', '0031_add_accesslog_brin_indexes')]

    operations = [
        migrations.AlterField(
            model_name='accesslog',
            name='report_type',
            field=models.ForeignKey(
                db_index=False, on_delete=django.db.models.deletion.CASCADE, to='logs.ReportType'
            ),
        ),
        migrations.AddIndex(
            model_name='accesslog',
            index=models.Index(
                fields=['report_type', 'organization'], name='logs_access_report__2ce170_idx'
            ),
        ),
    ]
