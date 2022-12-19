# Generated by Django 2.2.4 on 2019-08-05 16:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('core', '0005_user_language')]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='ext_id',
            field=models.PositiveIntegerField(
                blank=True, help_text='ID used in original source of this user data', null=True
            ),
        )
    ]
