# Generated by Django 3.1.3 on 2020-11-20 13:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('publications', '0022_datasource_set_null'),
    ]

    operations = [
        migrations.AlterField(
            model_name='platform',
            name='knowledgebase',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
