# Generated by Django 2.2.1 on 2019-06-26 13:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('organizations', '0002_nullable_internal_id')]

    operations = [
        migrations.AlterField(
            model_name='organization',
            name='ico',
            field=models.PositiveIntegerField(help_text='Business registration number'),
        ),
        migrations.AlterUniqueTogether(name='organization', unique_together={('ico', 'level')}),
    ]
