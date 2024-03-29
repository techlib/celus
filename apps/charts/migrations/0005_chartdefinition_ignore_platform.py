# Generated by Django 2.2.5 on 2019-12-02 15:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('charts', '0004_is_standard_view_and_position')]

    operations = [
        migrations.AddField(
            model_name='chartdefinition',
            name='ignore_platform',
            field=models.BooleanField(
                default=False,
                help_text='When checked, the chart will contain data for all platforms. This is '
                'useful to compare platforms for one title.',
            ),
        )
    ]
