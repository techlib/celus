# Generated by Django 2.2.4 on 2019-09-25 12:23

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [('annotations', '0001_initial')]

    operations = [
        migrations.RemoveField(model_name='annotation', name='report_type'),
        migrations.RemoveField(model_name='annotation', name='title'),
    ]
