# Generated by Django 3.2.15 on 2022-08-26 11:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('tags', '0003_tagging_batch')]

    operations = [
        migrations.AlterField(
            model_name='taggingbatch',
            name='state',
            field=models.CharField(
                choices=[
                    ('initial', 'Initial'),
                    ('preprocessing', 'Preprocessing'),
                    ('preflight', 'Preflight'),
                    ('importing', 'Importing'),
                    ('imported', 'Imported'),
                    ('prefailed', 'Preflight failed'),
                    ('failed', 'Import failed'),
                    ('undoing', 'Undoing'),
                ],
                default='initial',
                max_length=20,
            ),
        )
    ]
