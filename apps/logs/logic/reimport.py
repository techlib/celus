import os
from dataclasses import dataclass
from typing import Generator, Tuple, List

from django.contrib.postgres.aggregates import ArrayAgg
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import QuerySet, Exists, OuterRef, Q, F
from django.db.models.expressions import CombinedExpression
from django.db.transaction import atomic

from logs.exceptions import DataStructureError, SourceFileMissingError
from logs.logic.attempt_import import import_one_sushi_attempt
from logs.logic.custom_import import import_custom_data
from logs.models import ImportBatch, ManualDataUploadImportBatch, ManualDataUpload, AccessLog
from scheduler.models import FetchIntention
from sushi.models import SushiFetchAttempt, AttemptStatus


@dataclass
class MDUBatch:
    mdu: ManualDataUpload
    to_reimport: QuerySet[ImportBatch]
    to_delete: QuerySet[ImportBatch]


@dataclass
class ImportBatchReimport:
    # to reimport
    reimportable: QuerySet[ImportBatch]
    # should be deleted
    obsolete: QuerySet[ImportBatch]
    # cannot be reimported - no FA or MDU
    no_source: QuerySet[ImportBatch] = ImportBatch.objects.none()
    # clashing with `no_source`, cannot delete or reimport, because we do not know how the data
    # from those clashing import batches were mixed together
    blocked: QuerySet[ImportBatch] = ImportBatch.objects.none()

    def gen_mdu_batches(self,) -> Generator[MDUBatch, None, None]:
        """
        Import batches from one MDU have to be grouped together for reimport. This method
        generates tuples (mdu, [ibs_to_reimport], [ibs_to_delete]). The last member of the tuple
        are import batches that should be deleted because there are newer data.

        They would be deleted during the reimport of the newer IB, but may as well be deleted
        directly, so that they do not remain orphaned after the MDU is reimported
        """
        for rec in (
            self.reimportable.filter(mdu__isnull=False)
            .values('mdu')
            .annotate(ib_ids=ArrayAgg('id'))
        ):
            yield MDUBatch(
                ManualDataUpload.objects.get(pk=rec['mdu']),
                ImportBatch.objects.filter(pk__in=rec['ib_ids']),
                ImportBatch.objects.filter(mdu__id=rec['mdu']).exclude(pk__in=rec['ib_ids']),
            )


def find_import_batches_to_reimport(queryset: QuerySet[ImportBatch]) -> ImportBatchReimport:
    """
    Returns a queryset with import batches to re-import and import batches to delete.
    The ones to delete are those that are clashing with the reimported ones and are older.

    It prefers to reimport the newest import batches, but gives even more preference to those
    import batches for which a FetchAttempt or MDU exists.
    """
    newest = (
        queryset.filter(date__isnull=False)
        .annotate(
            has_fa=Exists(SushiFetchAttempt.objects.filter(import_batch_id=OuterRef('id'))),
            has_mdu=Exists(
                ManualDataUploadImportBatch.objects.filter(import_batch_id=OuterRef('id'))
            ),
            has_als=Exists(AccessLog.objects.filter(import_batch_id=OuterRef('id'))),
        )
        # combine has_fa and has_mdu into one field so that both have the same value when sorting
        .annotate(has_source=CombinedExpression(lhs=F('has_fa'), rhs=F('has_mdu'), connector="OR"))
        .order_by(
            'organization_id',
            'platform_id',
            'report_type_id',
            'date',
            '-has_als',
            '-has_source',
            '-created',
        )
        .distinct('organization_id', 'platform_id', 'report_type_id', 'date')
    )
    reimportable = queryset.filter(
        Q(sushifetchattempt__isnull=False) | Q(mdu__isnull=False), pk__in=newest
    )
    obsolete = queryset.exclude(pk__in=newest).filter(
        Exists(
            ImportBatch.objects.filter(
                organization_id=OuterRef('organization_id'),
                platform_id=OuterRef('platform_id'),
                report_type_id=OuterRef('report_type_id'),
                date=OuterRef('date'),
                pk__in=reimportable,
            )
        )
    )
    blocked = queryset.exclude(pk__in=newest).exclude(pk__in=obsolete)
    return ImportBatchReimport(
        reimportable=reimportable,
        no_source=queryset.filter(pk__in=newest, sushifetchattempt__isnull=True, mdu__isnull=True),
        obsolete=obsolete,
        blocked=blocked,
    )


def has_source_data_file(ib: ImportBatch) -> bool:
    """
    Checks if the import batch has a related object with source data and that the file at
    hand exists.
    """
    try:
        source_fa = ib.sushifetchattempt
    except ObjectDoesNotExist:
        try:
            source_mdu = ib.mdu.get()
        except ObjectDoesNotExist:
            return False
        else:
            try:
                return os.path.isfile(source_mdu.data_file.path)
            except ValueError:
                return False
    else:
        try:
            return os.path.isfile(source_fa.data_file.path)
        except ValueError:
            return False


def find_and_delete_clashing_data(ib: ImportBatch):
    """
    find and delete clashing ibs, fas and fis
    """
    clashing = ImportBatch.objects.filter(
        organization_id=ib.organization_id,
        platform_id=ib.platform_id,
        report_type_id=ib.report_type_id,
        date=ib.date,
    ).exclude(pk=ib.pk)
    FetchIntention.objects.filter(attempt__import_batch__in=clashing).delete()
    SushiFetchAttempt.objects.filter(import_batch__in=clashing).delete()
    clashing.delete()


@atomic
def reimport_import_batch_with_fa(ib: ImportBatch) -> ImportBatch:
    """
    Deletes the import batch and all import batches clashing with it. Reimports the data
    from a corresponding FA.

    MDU related import batches should be handled separately in `reimport_mdu_batch`
    """
    try:
        source_fa = ib.sushifetchattempt
    except ObjectDoesNotExist:
        raise DataStructureError('Import batch without FA')
    # check that we have the raw data before we delete anything
    if source_fa and not os.path.isfile(source_fa.data_file.path):
        raise SourceFileMissingError()

    if source_fa.status == AttemptStatus.NO_DATA:
        if (
            ImportBatch.objects.filter(
                organization_id=ib.organization_id,
                platform_id=ib.platform_id,
                report_type_id=ib.report_type_id,
                date=ib.date,
            )
            .annotate(has_als=Exists(AccessLog.objects.filter(import_batch_id=OuterRef('id'))))
            .filter(has_als=True)
            .exists()
        ):
            raise ValueError('Cannot use NO_DATA IB if there is one with data')

    find_and_delete_clashing_data(ib)
    # reimport the data if source is fa
    if source_fa.status != AttemptStatus.NO_DATA:
        # skip reprocessing of `NO_DATA` fetch attempts
        # the rationale is that we retry 3030 and similar error codes several times, and it
        # would be hard to guess from the data itself what should be the outcome. This way, we
        # simply trust our previous decision about assigning `NO_DATA` and go with it.
        # If we someday find that our `NO_DATA` decision process is flawed and need to reimport
        # we would need to remove this condition.
        source_fa.unprocess()
        import_one_sushi_attempt(source_fa)
    else:
        ib.save()  # update last_updated
    return source_fa.import_batch


@atomic
def reimport_mdu_batch(mdu_batch: MDUBatch):
    if not os.path.isfile(mdu_batch.mdu.data_file.path):
        raise SourceFileMissingError()
    # those to delete are simply deleted
    mdu_batch.to_delete.delete()
    # those to reimport are also deleted, but clashing IBs are deleted as well,
    # and we remember the months to reimport
    months = [ib.date.isoformat() for ib in mdu_batch.to_reimport]
    for ib in mdu_batch.to_reimport:
        find_and_delete_clashing_data(ib)
        ib.delete()
    import_custom_data(mdu_batch.mdu, mdu_batch.mdu.user, months=months)
