# Generated by Django 3.2.15 on 2022-08-30 13:38

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [('tags', '0004_alter_taggingbatch_state')]

    operations = [
        migrations.AlterModelOptions(
            name='tag', options={'ordering': ['name'], 'verbose_name': 'Tag'}
        )
    ]
