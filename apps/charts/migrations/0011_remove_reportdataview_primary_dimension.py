# Generated by Django 3.2.17 on 2023-02-14 12:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [('charts', '0010_chartdefinition_is_generic')]

    operations = [migrations.RemoveField(model_name='reportdataview', name='primary_dimension')]
