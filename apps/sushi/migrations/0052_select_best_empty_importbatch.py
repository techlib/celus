# Generated by Django 3.2.12 on 2022-04-28 15:04

import sys
from collections import Counter

from django.db import migrations
from django.db.models import Exists, OuterRef


def remove_obsolete_3030_fas_with_empty_ib(apps, schema_editor):
    """
    Finds all FAs with 3030 and empty IB for which there is also a matching FA containing data
    and deletes them.
    These are probably artifacts of not completely correct migrations of old data
    """
    SushiFetchAttempt = apps.get_model('sushi', 'SushiFetchAttempt')
    ImportBatch = apps.get_model('logs', 'ImportBatch')
    AccessLog = apps.get_model('logs', 'AccessLog')
    to_delete_fas = []
    to_delete_ibs = []
    # the following is a queryset to the newer FAs replacing the ones we are testing
    # these have to have an import batch and some data and match the FA at hand
    other_fa_qs = (
        SushiFetchAttempt.objects.filter(
            credentials_id=OuterRef('credentials_id'),
            counter_report_id=OuterRef('counter_report_id'),
            start_date=OuterRef('start_date'),
            end_date=OuterRef('end_date'),
        )
        .exclude(data_file='')
        .filter(import_batch_id__isnull=False)
        .filter(Exists(AccessLog.objects.filter(import_batch_id=OuterRef('import_batch_id'))))
    )
    for fa in (
        SushiFetchAttempt.objects.filter(import_batch_id__isnull=False, error_code='3030')
        .exclude(Exists(AccessLog.objects.filter(import_batch_id=OuterRef('import_batch_id'))))
        .filter(Exists(other_fa_qs))
    ):
        to_delete_fas.append(fa.pk)
        to_delete_ibs.append(fa.import_batch_id)
    ImportBatch.objects.filter(pk__in=to_delete_ibs).delete()
    SushiFetchAttempt.objects.filter(pk__in=to_delete_fas).delete()
    print("Removed obsolete 3030 FAs:", len(to_delete_fas), file=sys.stderr)


def fix_3030_fas_with_ib_and_empty_data_file(apps, schema_editor):
    """
    Because of the way we added an empty import batch to FAs with 3030, it could happen
    (and happened) that the import batch was added to the oldest FA which sometimes had the
    `data_file` attribute empty.

    To make the data reimportable and otherwise more consistent, we try to find such FAs with
    `import_batch` which have empty file and remove them if a replacement is present. We then add
    an empty IB to the newly selected FA.

    So this whole code is about replacing one empty FA with another empty FA, but which has
    a file associated, so it can be reimported
    """
    SushiFetchAttempt = apps.get_model('sushi', 'SushiFetchAttempt')
    ImportBatch = apps.get_model('logs', 'ImportBatch')
    AccessLog = apps.get_model('logs', 'AccessLog')
    to_delete = []
    stats = Counter()
    for fa in SushiFetchAttempt.objects.filter(
        import_batch_id__isnull=False, data_file='', error_code='3030'
    ).exclude(Exists(AccessLog.objects.filter(import_batch_id=OuterRef('import_batch_id')))):
        other_fas = (
            SushiFetchAttempt.objects.filter(
                credentials_id=fa.credentials_id,
                counter_report_id=fa.counter_report_id,
                start_date=fa.start_date,
                end_date=fa.end_date,
            )
            .exclude(data_file='')
            .filter(import_batch_id__isnull=True)
            .order_by('-last_updated')
        )
        if other_fas.exists():
            winner = other_fas[0]
            fa.import_batch.delete()
            to_delete.append(fa.pk)
            winner.import_batch = ImportBatch.objects.create(
                report_type_id=fa.counter_report.report_type_id,
                platform_id=fa.credentials.platform_id,
                organization_id=fa.credentials.organization_id,
                date=fa.start_date,
            )
            winner.save()
            stats['replaced'] += 1
        else:
            stats['unreplacable'] += 1
    SushiFetchAttempt.objects.filter(pk__in=to_delete).delete()
    print("Stats:", stats, file=sys.stderr)


class Migration(migrations.Migration):

    dependencies = [
        ('sushi', '0051_fetchattempt_remove_queue_stuff'),
        ('logs', '0065_remove_dimension_type'),
    ]

    operations = [
        migrations.RunPython(remove_obsolete_3030_fas_with_empty_ib, migrations.RunPython.noop),
        migrations.RunPython(fix_3030_fas_with_ib_and_empty_data_file, migrations.RunPython.noop),
    ]
