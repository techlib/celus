# Generated by Django 2.2.1 on 2019-08-08 07:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('logs', '0006_metric_interest_group')]

    operations = [
        migrations.AddField(
            model_name='metric',
            name='name_in_interest_group',
            field=models.CharField(
                blank=True,
                help_text='How is the metric called when interest sub-series are shown',
                max_length=250,
            ),
        ),
        migrations.AddField(
            model_name='metric',
            name='name_in_interest_group_cs',
            field=models.CharField(
                blank=True,
                help_text='How is the metric called when interest sub-series are shown',
                max_length=250,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='metric',
            name='name_in_interest_group_en',
            field=models.CharField(
                blank=True,
                help_text='How is the metric called when interest sub-series are shown',
                max_length=250,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='metric', name='name', field=models.CharField(blank=True, max_length=250)
        ),
        migrations.AlterField(
            model_name='metric',
            name='name_cs',
            field=models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AlterField(
            model_name='metric',
            name='name_en',
            field=models.CharField(blank=True, max_length=250, null=True),
        ),
    ]
