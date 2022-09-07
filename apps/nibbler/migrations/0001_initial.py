# Generated by Django 3.2.15 on 2022-08-09 13:37

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0016_taskprogress'),
    ]

    operations = [
        migrations.CreateModel(
            name='ParserDefinition',
            fields=[
                ('id', models.PositiveIntegerField(primary_key=True, serialize=False)),
                ('definition', models.JSONField()),
                ('version', models.PositiveIntegerField()),
                ('report_type_short_name', models.CharField(max_length=100)),
                ('report_type_ext_id', models.IntegerField(blank=True, null=True)),
                ('short_name', models.CharField(max_length=100)),
                (
                    'source',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to='core.datasource'
                    ),
                ),
            ],
            options={
                'verbose_name': 'Parser Definition',
                'verbose_name_plural': 'Parser Definitions',
            },
        ),
        migrations.AddConstraint(
            model_name='parserdefinition',
            constraint=models.UniqueConstraint(
                fields=('short_name', 'source'), name='parser_def_short_name_source_not_null'
            ),
        ),
    ]
