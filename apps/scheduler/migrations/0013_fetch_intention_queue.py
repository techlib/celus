# Generated by Django 3.1.13 on 2021-10-25 20:48
import django.db.models.deletion
from django.db import migrations, models
from django.db.migrations import RunPython


def create_queues(apps, schema_editor):
    FetchIntention = apps.get_model('scheduler', 'FetchIntention')
    FetchIntentionQueue = apps.get_model('scheduler', 'FetchIntentionQueue')
    chunk_size = 2000
    queues = []
    for fi in (
        FetchIntention.objects.values('queue_id')
        .annotate(min_pk=models.Min('pk'), max_pk=models.Max('pk'))
        .iterator(chunk_size)
    ):
        queues.append(
            FetchIntentionQueue(id=fi["queue_id"], start_id=fi["min_pk"], end_id=fi["max_pk"])
        )
        if len(queues) >= chunk_size:
            FetchIntentionQueue.objects.bulk_create(queues)
            queues = []

    FetchIntentionQueue.objects.bulk_create(queues)


class Migration(migrations.Migration):

    dependencies = [('scheduler', '0012_fill_queue_id')]

    operations = [
        migrations.CreateModel(
            name='FetchIntentionQueue',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False)),
                (
                    'end',
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='qend',
                        to='scheduler.fetchintention',
                    ),
                ),
                (
                    'start',
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='qstart',
                        to='scheduler.fetchintention',
                    ),
                ),
            ],
        ),
        RunPython(create_queues, RunPython.noop),
        migrations.AlterField(
            model_name='fetchintention',
            name='queue_id',
            field=models.ForeignKey(
                blank=True,
                help_text='Identifier of retry queue',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to='scheduler.fetchintentionqueue',
            ),
        ),
        migrations.RenameField(model_name="fetchintention", old_name="queue_id", new_name="queue"),
    ]
