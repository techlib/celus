# Generated by Django 2.2.5 on 2019-11-13 08:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0012_timestamps'),
    ]

    operations = [
        migrations.AlterModelOptions(name='organization', options={'ordering': ('name',)},),
    ]
