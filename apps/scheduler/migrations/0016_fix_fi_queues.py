# Generated by Django 3.2.15 on 2022-11-28 20:02

from django.db import migrations
from django.db.migrations import RunPython
from django.db.models import F, Q


def fix_queues(apps, schema_editor):
    FetchIntention = apps.get_model('scheduler', 'FetchIntention')
    FetchIntentionQueue = apps.get_model('scheduler', 'FetchIntentionQueue')

    # queue start with this fi, but fi has previous fi
    query = Q(queue__start_id=F('pk'), previous_intention__isnull=False)

    to_delete = []

    # one iteration should be enough here, we are fixing
    # the queue from the start and fi are sorted by pk
    for fi in FetchIntention.objects.filter(query).order_by('pk'):

        queue = fi.previous_intention.queue
        if not queue:
            # queue is missing for the previous intention
            # this should not happen, but lets fix that, just in case
            fi.previous_intention.queue = FetchIntentionQueue.objects.create(
                pk=fi.previous_intention.pk, start=fi.previous_intention, end=fi.previous_intention,
            )
            fi.previous_intention.save()
            queue = fi.previous_intention.queue

        queue.end = fi
        queue.save()
        to_delete.append(fi.queue_id)
        fi.queue = queue
        fi.save()

    # remove extra queues
    FetchIntentionQueue.objects.filter(pk__in=to_delete).delete()

    print(f"Fixed queues count: {len(to_delete)}")


class Migration(migrations.Migration):

    dependencies = [
        ('scheduler', '0015_fetchintention_timestamp'),
    ]

    operations = [
        RunPython(fix_queues, RunPython.noop),
    ]
