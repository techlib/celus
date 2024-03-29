# Generated by Django 3.1.8 on 2021-05-24 08:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('organizations', '0019_jsonfield')]

    operations = [
        migrations.AddConstraint(
            model_name='organization',
            constraint=models.UniqueConstraint(
                condition=models.Q(source__isnull=True),
                fields=('short_name',),
                name='organization_unique_global_shortname',
            ),
        ),
        migrations.AddConstraint(
            model_name='organization',
            constraint=models.UniqueConstraint(
                condition=models.Q(ext_id__isnull=True),
                fields=('short_name', 'source'),
                name='organization_unique_short_name_source',
            ),
        ),
    ]
