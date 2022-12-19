# Generated by Django 2.2.5 on 2019-12-02 16:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('charts', '0005_chartdefinition_ignore_platform')]

    operations = [
        migrations.AddField(
            model_name='chartdefinition',
            name='scope',
            field=models.CharField(
                choices=[('', 'any'), ('platform', 'platform'), ('title', 'title')],
                default='',
                max_length=10,
            ),
        )
    ]
