from datetime import date
from typing import Dict, Iterable, Optional, Tuple

from core.logic.dates import months_in_range
from django.db.models import Count, Exists, Max, Min, OuterRef, Q, QuerySet, Subquery, Sum, Value
from logs.models import AccessLog, ImportBatch, OrganizationPlatform, ReportType
from organizations.models import Organization
from publications.models import Platform, PlatformTitle, Title
from sushi.models import SushiCredentials


class DataCoverageExtractor:
    def __init__(
        self,
        report_type: ReportType,
        organization: Optional[Organization] = None,
        platform: Optional[Platform] = None,
        title: Optional[Title] = None,
        split_by_org: bool = False,
        split_by_platform: bool = False,
        start_month: date = None,
        end_month: date = None,
        accessible_organizations: Optional[Iterable[Organization]] = None,
    ):
        """
        :param report_type:
        :param organization: limit the data to this organization
        :param platform: limit the data to this platform
        :param title: limit the data to this title by only considering platforms having that title
        :param split_by_org: split resulting data by organization
        :param split_by_platform: split resulting data by platform
        :param start_month: if not given, it will be obtained from the database
        :param end_month: if not given, it will be obtained from the database
        :param accessible_organizations: organization accessible by the user at hand (if any)
        """
        self.report_type = report_type
        self.organization = organization
        self.platform = platform
        self.title = title
        self.split_by_org = split_by_org
        self.split_by_platform = split_by_platform
        self.start_month = start_month
        self.end_month = end_month
        self.accessible_organizations = (
            accessible_organizations
            if accessible_organizations is not None
            else Organization.objects.all()
        )

    @property
    def extra_filters(self) -> list:
        extra_filters = []
        if self.platform:
            extra_filters.append(Q(platform=self.platform))
        if self.organization:
            extra_filters.append(Q(organization=self.organization))
        if self.title:
            # we need to filter the platforms having this title
            extra_filters.append(
                Q(
                    Exists(
                        PlatformTitle.objects.filter(
                            title=self.title, platform=OuterRef('platform')
                        )
                    )
                )
            )
        return extra_filters

    @property
    def split_by(self) -> list:
        split_by = []  # this is how the data will be split
        if self.split_by_org:
            split_by.append('organization_id')
        if self.split_by_platform:
            split_by.append('platform_id')
        return split_by

    def create_rt_qs(self) -> QuerySet[ReportType]:
        if self.report_type.is_interest_rt:
            return ReportType.objects.filter(platforminterestreport__isnull=False)
        return ReportType.objects.filter(pk=self.report_type.pk)

    def get_basic_ib_qs(self) -> QuerySet[ImportBatch]:
        return ImportBatch.objects.filter(
            report_type__in=self.create_rt_qs(),
            organization__in=self.accessible_organizations,
            *self.extra_filters,
        )

    def _check_dates(self) -> bool:
        """
        Returns True if the dates are set, otherwise returns False meaning there is no
        data from which to extract the dates.
        :return:
        """
        if not (self.start_month and self.end_month):
            # we need to get the data range from the data itself
            date_range = self.get_basic_ib_qs().aggregate(
                min_date=Min('date'), max_date=Max('date')
            )
            if date_range['min_date']:
                # min_date could be None if there are no data
                if not self.start_month:
                    self.start_month = date_range['min_date']
                if not self.end_month:
                    self.end_month = date_range['max_date']
                return True
            else:
                # there is no ImportBatch
                return False
        return True

    def get_maximum_ib_counts(self) -> Dict[Tuple, Dict]:
        """
        For each possible group (by month and maybe organization or platform) returns the
        maximum number of import batches that could exist to give full data presence
        :return:
        """
        # op_counts is the number of organization-platforms for each split_by key
        # it is used to determine the maximum possible number of import batches which
        # can occur for one month for the key at hand
        # It is not easy to determine which Organization-Platforms combinations use a
        # specific report type - here we use two tests - one is that credentials exist
        # for that combination, the second is that an import batch exists

        rt_qs = self.create_rt_qs()
        basic_qs = OrganizationPlatform.objects.filter(
            *self.extra_filters,
            Exists(
                SushiCredentials.objects.filter(
                    organization=OuterRef('organization'),
                    platform=OuterRef('platform'),
                    counterreportstocredentials__counter_report__report_type__in=rt_qs,
                )
            )
            | Exists(
                ImportBatch.objects.filter(
                    report_type__in=rt_qs,
                    organization=OuterRef('organization'),
                    platform=OuterRef('platform'),
                )
            ),
            organization__in=self.accessible_organizations,
        )
        if self.report_type.is_interest_rt:
            # in case that self.report_type is interest, we need to take into account all
            # associated report types which define interest, but only count those that are not
            # superseded to prevent double-counting
            #
            # this approach still has a problem. In real world, both JR1 and BR2 are superseded
            # by TR, so the actual number of import batches that should be present depends on
            # the presence of TR data - if it is there, only one IB is OK, if it is not there,
            # then 2 IBs (for JR1 and BR2) are needed.
            # this is unfortunately too involved for now, so I have to think about it a bit more...

            qs = (
                basic_qs.annotate(
                    foo=Value(42),  # dummy value to have something if split_by is empty
                    # the following is a convoluted way of making the Sum of rt_count possible
                    # because a more straightforward way complains that is it not possible
                    # to do Sum on an aggregate value
                    rt_count=Subquery(
                        ReportType.objects.filter(
                            platforminterestreport__platform=OuterRef('platform'),
                            superseeded_by__isnull=True,
                        )
                        .annotate(x=Value(7))
                        .values('x')
                        .annotate(c=Count('id'))
                        .values('c')
                    ),
                )
                .values('foo', *self.split_by)
                .annotate(op_count=Sum('rt_count'))
            )
        else:
            qs = (
                basic_qs.annotate(
                    foo=Value(42)  # dummy value to have something if split_by is empty
                )
                .values('foo', *self.split_by)
                .annotate(op_count=Count('id'))
            )
        op_counts = {tuple(rec[key] for key in self.split_by): rec['op_count'] for rec in qs}
        return op_counts

    def get_coverage_data(self) -> Dict[Tuple, Dict]:
        if not self._check_dates():
            return {}
        max_ib_counts = self.get_maximum_ib_counts()
        split_by = self.split_by

        qs = (
            self.get_basic_ib_qs()
            .filter(date__gte=self.start_month, date__lte=self.end_month)
            .values('date', *split_by)
            .annotate(ib_count=Count('pk', distinct=True))
            .order_by('date', *split_by)
        )
        if self.report_type.is_interest_rt:
            # only count import batches which really have interest data
            # not those that were skipped during interest computation (probably because
            # the RT was superseded by a newer one).
            qs = qs.filter(
                Exists(
                    AccessLog.objects.filter(
                        report_type=self.report_type, import_batch_id=OuterRef('pk')
                    )
                )
            )

        # join the data from max_ib_counts with the actual counts of IBs
        data = {(rec['date'], *(rec[k] for k in split_by)): rec for rec in qs}
        for month in months_in_range(self.start_month, self.end_month):
            for key, op_count in max_ib_counts.items():
                super_key = (month, *key)
                if super_key not in data:
                    data[super_key] = {
                        'date': month,
                        **dict(zip(split_by, key)),  # the key as dict
                        'ib_count': 0,
                        'ib_max': op_count,
                        'ratio': 0,
                    }
                else:
                    data[super_key].update(
                        {
                            'ib_max': op_count,
                            'ratio': data[super_key]['ib_count'] / op_count if op_count else None,
                        }
                    )
        return data
