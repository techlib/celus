# Generated by Django 2.2.1 on 2019-06-28 09:01

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='ext_id',
            field=models.PositiveIntegerField(
                help_text='ID used in original source of this user data', null=True
            ),
        ),
        migrations.CreateModel(
            name='Identity',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                (
                    'identity',
                    models.CharField(
                        db_index=True,
                        help_text='External identifier of the person, usually email',
                        max_length=100,
                        unique=True,
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
        ),
    ]
