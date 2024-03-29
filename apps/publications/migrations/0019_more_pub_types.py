# Generated by Django 2.2.13 on 2020-07-20 17:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('publications', '0018_platformtitle_unique_constraint')]

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
                    ('M', 'Multimedia'),
                    ('A', 'Article'),
                    ('S', 'Book segment'),
                    ('T', 'Dataset'),
                    ('P', 'Platform'),
                    ('I', 'Repository item'),
                    ('H', 'Thesis or dissertation'),
                ],
                max_length=1,
                verbose_name='Publication type',
            ),
        )
    ]
