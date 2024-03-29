# Generated by Django 3.1.3 on 2020-11-23 15:06

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('scheduler', '0007_fetchintention_one_to_one_attempt')]

    operations = [
        migrations.AddField(
            model_name='scheduler',
            name='current_celery_task_id',
            field=models.UUIDField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='scheduler',
            name='current_intention',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='current_scheduler',
                to='scheduler.fetchintention',
            ),
        ),
        migrations.AddField(
            model_name='scheduler',
            name='current_start',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='fetchintention',
            name='scheduler',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='intentions',
                to='scheduler.scheduler',
            ),
        ),
        migrations.AlterField(
            model_name='fetchintention',
            name='when_processed',
            field=models.DateTimeField(
                blank=True, help_text='When fetch intention was processed', null=True
            ),
        ),
    ]
