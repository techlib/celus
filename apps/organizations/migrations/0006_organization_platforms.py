# Generated by Django 2.2.1 on 2019-07-01 18:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('logs', '0004_source_field'),
        ('publications', '0004_pub_type_verbose_name'),
        ('organizations', '0005_organization_users'),
    ]

    operations = [
        migrations.AddField(
            model_name='organization',
            name='platforms',
            field=models.ManyToManyField(
                through='logs.OrganizationPlatform', to='publications.Platform'
            ),
        )
    ]
