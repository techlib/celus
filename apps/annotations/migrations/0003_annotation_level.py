# Generated by Django 2.2.4 on 2019-09-25 12:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('annotations', '0002_no_title_no_report_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='annotation',
            name='level',
            field=models.CharField(choices=[('info', 'info'), ('important', 'important')], default='info', max_length=20),
        ),
    ]