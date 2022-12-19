# Generated by Django 2.2.4 on 2019-08-05 16:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('publications', '0007_title_unique_together')]

    operations = [
        migrations.AlterField(
            model_name='title',
            name='pub_type',
            field=models.CharField(
                choices=[
                    ('B', 'Book'),
                    ('J', 'Journal'),
                    ('U', 'Unknown'),
                    ('D', 'Database'),
                    ('O', 'Other'),
                    ('R', 'Report'),
                    ('N', 'Newspaper'),
                ],
                max_length=1,
                verbose_name='Publication type',
            ),
        )
    ]
