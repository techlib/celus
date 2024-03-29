# Generated by Django 2.2.4 on 2019-09-04 15:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('logs', '0017_virtual_report_types')]

    operations = [
        migrations.AddField(
            model_name='virtualreporttype',
            name='desc_cs',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='virtualreporttype',
            name='desc_en',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='virtualreporttype',
            name='name_cs',
            field=models.CharField(max_length=250, null=True),
        ),
        migrations.AddField(
            model_name='virtualreporttype',
            name='name_en',
            field=models.CharField(max_length=250, null=True),
        ),
    ]
