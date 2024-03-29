# Generated by Django 3.2.13 on 2022-06-02 13:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('logs', '0069_merge_20220603_1325')]

    operations = [
        migrations.AddField(
            model_name='reporttype',
            name='ext_id',
            field=models.PositiveIntegerField(blank=True, default=None, null=True, unique=True),
        ),
        migrations.AddConstraint(
            model_name='reporttype',
            constraint=models.UniqueConstraint(
                fields=('source', 'ext_id'), name='report_type_unique_ext_id_per_source'
            ),
        ),
    ]
