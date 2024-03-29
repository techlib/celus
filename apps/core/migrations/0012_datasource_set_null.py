# Generated by Django 3.0.10 on 2020-11-03 08:18

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('core', '0011_datasource_knowledgebase')]

    operations = [
        migrations.AlterField(
            model_name='identity',
            name='source',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='core.DataSource',
            ),
        ),
        migrations.AlterField(
            model_name='user',
            name='source',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='core.DataSource',
            ),
        ),
    ]
