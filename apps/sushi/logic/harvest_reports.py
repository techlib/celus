from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import List, Optional

from dateutil.relativedelta import relativedelta
from django.db.models import BooleanField, Case, F, Min, QuerySet, Value, When
from django.db.models.functions import Greatest
from logs.models import ImportBatch
from organizations.models import Organization

from sushi import models


@dataclass
class DataCounts:
    total: int = 0  # data that should be present
    empty: int = 0  # empty import batch
    sushi: int = 0  # downloaded using sushi
    manual: int = 0  # manually uploaded
    missing: int = 0  # import batch missing

    def process(self, annotated_ib: Optional[ImportBatch]):
        self.total += 1
        if ib := annotated_ib:
            self.empty += 0 if ib.has_logs else 1
            self.manual += 1 if ib.mdu_id else 0
            self.sushi += 1 if ib.attempt_id else 0
        else:
            self.missing += 1

    def __add__(self, other: "DataCounts") -> "DataCounts":
        return DataCounts(
            total=self.total + other.total,
            empty=self.empty + other.empty,
            sushi=self.sushi + other.sushi,
            manual=self.manual + other.manual,
            missing=self.missing + other.missing,
        )

    def __iadd__(self, other: "DataCounts"):
        self.total += other.total
        self.empty += other.empty
        self.sushi += other.sushi
        self.manual += other.manual
        self.missing += other.missing
        return self

    @property
    def success_rate(self) -> Optional[float]:
        if self.total:
            return (self.total - self.missing) / self.total * 100.0


@dataclass
class HarvestReport:
    organization: Organization
    month: date
    credentials: List[models.SushiCredentials]
    success_rate: Optional[float]
    data_counts: DataCounts


def make_harvest_reports(
    organizations: QuerySet[Organization], month: Optional[date] = None
) -> List[HarvestReport]:
    month = month or date.today().replace(day=1) - relativedelta(months=2)
    org_map = {e.pk: e for e in organizations}
    data_matrix = models.CounterReportsToCredentials.objects.filter(
        credentials__organization__in=list(organizations)
    ).values_list(
        "credentials__organization_id", "credentials__platform_id", "counter_report__report_type_id"
    )
    data_counts = defaultdict(DataCounts)
    matrix = {
        (e.organization_id, e.platform_id, e.report_type_id): e
        for e in ImportBatch.objects.filter(
            date=month,
            report_type__counterreporttype__isnull=False,  # only counter data
        )
        .data_matrix(organizations=organizations)
        .select_related("sushifetchattempt", "sushifetchattempt__credentials")
    }
    empty_credentials_ids = set()
    for organization_id, platform_id, report_type_id in data_matrix:
        matrix_record = matrix.get((organization_id, platform_id, report_type_id))
        data_counts[org_map[organization_id]].process(matrix_record)
        if matrix_record and not matrix_record.has_logs and matrix_record.attempt_id:
            empty_credentials_ids.add(matrix_record.sushifetchattempt.credentials_id)

    cred_qs = (
        models.SushiCredentials.objects.filter(organization__in=list(organizations))
        .annotate(
            broken_since_cred=Min("first_broken_attempt__timestamp"),
            broken_since_rt=Min("counterreportstocredentials__first_broken_attempt__timestamp"),
            broken_since=Greatest(F("broken_since_cred"), F("broken_since_rt")),
            has_empty_data=Case(
                When(pk__in=empty_credentials_ids, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            ),
        )
        .annotate_verified()
        .select_related("platform", "organization")
    ).order_by("pk")

    return [
        HarvestReport(
            organization=org,
            month=month,
            credentials=[e for e in cred_qs if e.organization == org],
            success_rate=data_counts[org].success_rate,
            data_counts=data_counts[org],
        )
        for org in organizations
    ]
