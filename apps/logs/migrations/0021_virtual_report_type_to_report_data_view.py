# Generated by Django 2.2.4 on 2019-09-09 08:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [('core', '0007_timestamps'), ('logs', '0020_materialized_interest_support')]

    operations = [
        migrations.RenameModel(old_name='VirtualReportType', new_name='ReportDataView'),
        migrations.RemoveField(model_name='metric', name='interest_group'),
        migrations.RemoveField(model_name='metric', name='name_in_interest_group'),
        migrations.RemoveField(model_name='metric', name='name_in_interest_group_cs'),
        migrations.RemoveField(model_name='metric', name='name_in_interest_group_en'),
    ]
