# Generated by Django 2.2.4 on 2019-08-07 13:19

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0011_userorganization_source'),
    ]

    operations = [
        migrations.AddField(
            model_name='organization',
            name='created',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='organization',
            name='last_modified',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='userorganization',
            name='created',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='userorganization',
            name='last_modified',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
