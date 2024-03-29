# Generated by Django 2.2.1 on 2019-08-19 07:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('publications', '0008_more_pub_types')]

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
                ],
                max_length=1,
                verbose_name='Publication type',
            ),
        )
    ]
