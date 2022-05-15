from django.conf import settings
from hcube.api.backend import CubeBackend
from hcube.api.models.cube import Cube
from hcube.api.models.dimensions import IntDimension, DateDimension
from hcube.api.models.materialized_views import AggregatingMaterializedView
from hcube.api.models.metrics import IntMetric
from hcube.backends.clickhouse import ClickhouseCubeBackend, IndexDefinition

from logs.models import AccessLog, ImportBatch, ReportType

ch_backend = ClickhouseCubeBackend(
    database=settings.CLICKHOUSE_DB,
    user=settings.CLICKHOUSE_USER,
    password=settings.CLICKHOUSE_PASSWORD,
    host=settings.CLICKHOUSE_HOST,
    port=settings.CLICKHOUSE_PORT,
    secure=settings.CLICKHOUSE_SECURE,
)


class AccessLogCube(Cube):

    # dimensions
    id = IntDimension(signed=False, bits=64)
    report_type_id = IntDimension(signed=False, bits=32)
    metric_id = IntDimension(signed=False, bits=32)
    organization_id = IntDimension(signed=False, bits=32)
    platform_id = IntDimension(signed=False, bits=32)
    target_id = IntDimension(signed=False, bits=32)
    dim1 = IntDimension(signed=False, bits=32)
    dim2 = IntDimension(signed=False, bits=32)
    dim3 = IntDimension(signed=False, bits=32)
    dim4 = IntDimension(signed=False, bits=32)
    dim5 = IntDimension(signed=False, bits=32)
    dim6 = IntDimension(signed=False, bits=32)
    dim7 = IntDimension(signed=False, bits=32)
    date = DateDimension()
    import_batch_id = IntDimension(signed=False, bits=32)
    # metrics
    value = IntMetric(signed=False, bits=32)

    class Clickhouse:
        # primary key must be prefix of the sorting key
        primary_key = ['report_type_id', 'organization_id', 'platform_id']
        # sorting key must contain all dimensions to prevent collapsing in CH
        sorting_key = [
            'report_type_id',
            'organization_id',
            'platform_id',
            'date',
            'metric_id',
            'target_id',
            'dim1',
            'dim2',
            'dim3',
            'dim4',
            'dim5',
            'dim6',
            'dim7',
            'import_batch_id',
            'id',
        ]
        indexes = [
            # skipping index to make finding data by import batch faster
            # reduces time to delete import batch data by several factors of magnitude for big dbs
            IndexDefinition(
                name='idx_import_batch_id',
                expression='import_batch_id',
                type='set(0)',
                granularity=1,
            )
        ]

    @classmethod
    def translate_accesslog_to_cube(cls, accesslog: AccessLog) -> 'AccessLogCubeRecord':
        return AccessLogCubeRecord(
            id=accesslog.id,
            report_type_id=accesslog.report_type_id or 0,
            metric_id=accesslog.metric_id or 0,
            organization_id=accesslog.organization_id or 0,
            platform_id=accesslog.platform_id or 0,
            target_id=accesslog.target_id or 0,
            dim1=accesslog.dim1 or 0,
            dim2=accesslog.dim2 or 0,
            dim3=accesslog.dim3 or 0,
            dim4=accesslog.dim4 or 0,
            dim5=accesslog.dim5 or 0,
            dim6=accesslog.dim6 or 0,
            dim7=accesslog.dim7 or 0,
            date=accesslog.date or 0,
            import_batch_id=accesslog.import_batch_id,
            value=accesslog.value,
        )

    @classmethod
    def translate_accesslog_dict_to_cube(cls, accesslog: dict) -> 'AccessLogCubeRecord':
        return AccessLogCubeRecord(
            id=accesslog['id'],
            report_type_id=accesslog['report_type_id'] or 0,
            metric_id=accesslog['metric_id'] or 0,
            organization_id=accesslog['organization_id'] or 0,
            platform_id=accesslog['platform_id'] or 0,
            target_id=accesslog['target_id'] or 0,
            dim1=accesslog['dim1'] or 0,
            dim2=accesslog['dim2'] or 0,
            dim3=accesslog['dim3'] or 0,
            dim4=accesslog['dim4'] or 0,
            dim5=accesslog['dim5'] or 0,
            dim6=accesslog['dim6'] or 0,
            dim7=accesslog['dim7'] or 0,
            date=accesslog['date'] or 0,
            import_batch_id=accesslog['import_batch_id'],
            value=accesslog['value'],
        )

    @classmethod
    def sync_import_batch_with_cube(
        cls, backend: CubeBackend, import_batch: ImportBatch, batch_size=10_000
    ) -> int:
        """
        Writes all accesslogs from an import_batch into the cube using backend `backend`.
        Writes are performed in batches of `batch_size` records in order to minimize memory
        requirements.
        Returns number of records synced.

        Note: we do not care about duplicates in the cube because this is primarily targetting
        clickhouse where records with same key will be merged.
        """
        to_write = []
        out = 0
        # only sync accesslogs which are not for materialized reports - in ClickHouse, we have
        # a better way of optimizing access than materialized reports (e.g. projections)
        for al in (
            import_batch.accesslog_set.filter(report_type__materialization_spec__isnull=True)
            .values()
            .iterator()
        ):
            to_write.append(cls.translate_accesslog_dict_to_cube(al))
            if len(to_write) >= batch_size:
                backend.store_records(cls, to_write)
                out += len(to_write)
                to_write = []
        if to_write:
            backend.store_records(cls, to_write)
        return out + len(to_write)

    @classmethod
    def sync_import_batch_interest_with_cube(
        cls, backend: CubeBackend, import_batch: ImportBatch, batch_size=10_000
    ) -> int:
        """
        Only syncs interest for specific batch by deleting all previous interest records for
        that batch and then recreating it.
        """
        interest_rt = ReportType.objects.get_interest_rt()
        to_write = []
        out = 0
        backend.delete_records(
            AccessLogCube.query().filter(
                import_batch_id=import_batch.pk, report_type_id=interest_rt.pk
            )
        )
        for al in import_batch.accesslog_set.filter(report_type=interest_rt).values().iterator():
            to_write.append(cls.translate_accesslog_dict_to_cube(al))
            if len(to_write) >= batch_size:
                backend.store_records(cls, to_write)
                out += len(to_write)
                to_write = []
        if to_write:
            backend.store_records(cls, to_write)
        return out + len(to_write)

    @classmethod
    def delete_import_batch(cls, backend: CubeBackend, import_batch_id: int):
        backend.delete_records(AccessLogCube.query().filter(import_batch_id=import_batch_id))


AccessLogCubeRecord = AccessLogCube.record_type()


class PlatformTitleOrganization(AggregatingMaterializedView):

    cube = AccessLogCube
    preserved_dimensions = ['target_id', 'platform_id', 'organization_id', 'date']
    aggregated_metrics = ['value']


class PlatformTitleOrganizationProjection(AggregatingMaterializedView):

    cube = AccessLogCube
    preserved_dimensions = ['target_id', 'platform_id', 'organization_id', 'date']
    aggregated_metrics = ['value']
    projection = True


class OrganizationImportantTitles(AggregatingMaterializedView):

    cube = AccessLogCube
    preserved_dimensions = ['report_type_id', 'organization_id', 'dim1', 'date', 'target_id']
    aggregated_metrics = ['value']
    projection = False
