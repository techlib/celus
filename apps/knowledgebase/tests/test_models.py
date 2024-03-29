import copy
import json
import re
import typing
import uuid
from importlib.metadata import version
from unittest.mock import patch

import pytest
import requests_mock
from core.models import DataSource
from django.utils.timezone import now
from knowledgebase.models import (
    ParserDefinitionImportAttempt,
    PlatformImportAttempt,
    ReportTypeImportAttempt,
    RouterSyncAttempt,
)
from logs.models import ReportInterestMetric, ReportType
from publications.models import Platform, PlatformInterestReport

from test_fixtures.entities.api import OrganizationAPIKeyFactory
from test_fixtures.entities.data_souces import DataSourceFactory
from test_fixtures.entities.logs import ImportBatchFactory
from test_fixtures.entities.platforms import PlatformFactory
from test_fixtures.scenarios.basic import (  # noqa - fixtures
    data_sources,
    interests,
    metrics,
    organizations,
    parser_definitions,
    platforms,
    report_types,
)

from . import (
    PLATFORM_INPUT_DATA,
    PLATFORM_INPUT_DATA2,
    REPORT_TYPE_INPUT_DATA,
    REPORT_TYPE_INPUT_DATA2,
)


@pytest.mark.django_db
class TestPlatformImportAttempt:
    @pytest.mark.parametrize(
        (
            "error",
            "data_hash",
            "started_timestamp",
            "end_timestamp",
            "processing_timestamp",
            "state",
            "failed",
            "success",
            "running",
        ),
        (
            (
                'error occured',
                'a' * 64,
                now(),
                now(),
                now(),
                PlatformImportAttempt.State.FAILED,
                True,
                False,
                False,
            ),
            (
                None,
                'a' * 64,
                None,
                now(),
                now(),
                PlatformImportAttempt.State.QUEUE,
                False,
                False,
                True,
            ),
            (
                None,
                None,
                now(),
                now(),
                now(),
                PlatformImportAttempt.State.DOWNLOADING,
                False,
                False,
                True,
            ),
            (
                None,
                'a' * 64,
                now(),
                None,
                now(),
                PlatformImportAttempt.State.PROCESSING,
                False,
                False,
                True,
            ),
            (
                None,
                'a' * 64,
                now(),
                now(),
                None,
                PlatformImportAttempt.State.SKIPPED,
                False,
                True,
                False,
            ),
            (
                None,
                'a' * 64,
                now(),
                now(),
                now(),
                PlatformImportAttempt.State.SUCCESS,
                False,
                True,
                False,
            ),
        ),
    )
    def test_states(
        self,
        error,
        data_hash,
        started_timestamp,
        end_timestamp,
        processing_timestamp,
        state,
        failed,
        success,
        running,
    ):
        attempt = PlatformImportAttempt(
            error=error,
            data_hash=data_hash,
            started_timestamp=started_timestamp,
            end_timestamp=end_timestamp,
            processing_timestamp=processing_timestamp,
        )
        assert attempt.status == state
        assert attempt.running == running
        assert attempt.failed == failed
        assert attempt.success == success

    def test_process(self, data_sources, report_types):

        attempt = PlatformImportAttempt(source=data_sources["brain"])
        attempt.save()

        attempt.process(PLATFORM_INPUT_DATA)

        default_rt_pks = set(
            ReportType.objects.filter(default_platform_interest=True).values_list(
                'short_name', flat=True
            )
        )

        # Check update
        assert attempt.stats == {"created": 3, "total": 3}

        # Check created platforms
        platform1 = Platform.objects.get(short_name="AAP")
        assert platform1.url == "https://www.aap.org/"
        assert platform1.provider == "AAP"
        assert platform1.name == "AAP - American Academy of Pediatrics"
        assert platform1.ext_id == 328
        assert platform1.counter_registry_id is None
        assert platform1.knowledgebase["providers"] == PLATFORM_INPUT_DATA[0]["providers"]
        assert platform1.knowledgebase["report_types"] == PLATFORM_INPUT_DATA[0]["report_types"]
        assert platform1.knowledgebase["platform_filter"] is None
        assert (
            set(
                platform1.platforminterestreport_set.values_list(
                    'report_type__short_name', flat=True
                )
            )
            == default_rt_pks
        ), "Interest report types created check"

        platform2 = Platform.objects.get(short_name="AACR")
        assert platform2.url == "https://www.aacr.org/"
        assert platform2.provider == "AACR"
        assert platform2.name == "American Association for Cancer Research"
        assert platform2.ext_id == 327
        assert platform2.counter_registry_id == uuid.UUID("11111111-1111-1111-1111-111111111111")
        assert platform2.knowledgebase["providers"] == PLATFORM_INPUT_DATA[1]["providers"]
        assert platform2.knowledgebase["report_types"] == PLATFORM_INPUT_DATA[1]["report_types"]
        assert (
            platform2.knowledgebase["platform_filter"] == PLATFORM_INPUT_DATA[1]["platform_filter"]
        )

        assert (
            set(
                platform2.platforminterestreport_set.values_list(
                    'report_type__short_name', flat=True
                )
            )
            == default_rt_pks
        ), "Interest report types created check"

        platform3 = Platform.objects.get(short_name="APS")
        assert platform3.url == "https://www.journals.aps.org/"
        assert platform3.provider == "APS"
        assert platform3.name == "APS"
        assert platform3.ext_id == 339
        assert platform3.duplicates == [999, 888]
        assert platform3.counter_registry_id == uuid.UUID("00000000-0000-0000-0000-000000000000")
        assert platform3.knowledgebase["providers"] == []
        assert platform3.knowledgebase["report_types"] == []
        assert platform3.knowledgebase["platform_filter"] is None
        assert (
            set(
                platform3.platforminterestreport_set.values_list(
                    'report_type__short_name', flat=True
                )
            )
            == default_rt_pks
        ), "Interest report types created check"

        # Same data
        attempt = PlatformImportAttempt(source=data_sources["brain"])
        attempt.save()
        attempt.process(PLATFORM_INPUT_DATA)
        assert attempt.stats == {"same": 3, "total": 3}

        # Update field
        input_data = copy.deepcopy(PLATFORM_INPUT_DATA)
        input_data[1]["providers"] = []
        attempt.process(input_data)
        assert attempt.stats == {"updated": 1, "same": 2, "total": 3}

        platform = Platform.objects.get(short_name="AACR")
        assert platform.knowledgebase["providers"] == []
        assert platform.knowledgebase["report_types"] == PLATFORM_INPUT_DATA[1]["report_types"]

    @pytest.mark.parametrize(
        "strategy,count,no_source,erms",
        (
            (PlatformImportAttempt.MergeStrategy.NONE, 8, False, False),
            (PlatformImportAttempt.MergeStrategy.EMPTY_SOURCE, 7, True, False),
            (PlatformImportAttempt.MergeStrategy.ALL, 6, True, True),
        ),
    )
    def test_process_merge_strategies(
        self, strategy, count, no_source, erms, data_sources, report_types
    ):
        other_data_source = DataSourceFactory(
            type=DataSource.TYPE_KNOWLEDGEBASE,
            short_name="other",
            url="https://other.example.com",
            token="f" * 64,
        )
        platform_wiped = PlatformFactory(
            short_name="wiped_knowledgebase",
            knowledgebase={"some": "data1"},
            source=data_sources["brain"],
        )
        platform_no_wiped = PlatformFactory(
            short_name="no_wiped_knowledgebase", knowledgebase={"some": "data2"}, source=None
        )
        platform_no_source = PlatformFactory(source=None, short_name="AAP")
        platform_erms = PlatformFactory(source=data_sources["api"], short_name="AACR")
        platform_other_knowledgebase = PlatformFactory(source=other_data_source, short_name="APS")
        other_source = platform_other_knowledgebase.source
        other_ext_id = platform_other_knowledgebase.ext_id

        PlatformImportAttempt.objects.create(source=data_sources["brain"]).process(
            PLATFORM_INPUT_DATA, strategy
        )

        assert Platform.objects.count() == count
        if no_source:
            platform_no_source.refresh_from_db()
            assert platform_no_source.ext_id == 328
            assert platform_no_source.source == data_sources["brain"]

        if erms:
            platform_erms.refresh_from_db()
            assert platform_erms.ext_id == 327
            assert platform_erms.source == data_sources["brain"]

        # make sure that records from other knowledgebase remains the same
        platform_other_knowledgebase.refresh_from_db()
        assert platform_other_knowledgebase.ext_id == other_ext_id
        assert platform_other_knowledgebase.source == other_source

        platform_wiped.refresh_from_db()
        assert platform_wiped.knowledgebase is None, "KB from same source is wiped"

        platform_no_wiped.refresh_from_db()
        assert platform_no_wiped.knowledgebase == {"some": "data2"}, "KB from other source remain"

    def test_process_merge_strategies_more_that_one_record(self, data_sources, report_types):

        # Create multiple for ALL strategy
        platform_no_source1 = PlatformFactory(source=None, short_name="AAP")
        no_source1_values = Platform.objects.values().get(pk=platform_no_source1.pk)
        platform_erms = PlatformFactory(source=data_sources["api"], short_name="AAP")
        erms_values = Platform.objects.values().get(pk=platform_erms.pk)

        PlatformImportAttempt.objects.create(source=data_sources["brain"]).process(
            PLATFORM_INPUT_DATA, PlatformImportAttempt.MergeStrategy.ALL
        )
        platform_with_removed_id = Platform.objects.get(short_name="AACR")
        assert platform_with_removed_id.counter_registry_id == uuid.UUID(
            "11111111-1111-1111-1111-111111111111"
        )
        assert Platform.objects.count() == 4
        assert Platform.objects.values().get(pk=platform_no_source1.pk) == no_source1_values
        assert Platform.objects.values().get(pk=platform_erms.pk) == erms_values

        # Create multiple for EMPTY_SOURCE strategy
        platform_no_source2 = PlatformFactory(source=None, short_name="ABC")
        PlatformImportAttempt.objects.create(source=data_sources["brain"]).process(
            PLATFORM_INPUT_DATA2, PlatformImportAttempt.MergeStrategy.EMPTY_SOURCE
        )
        assert Platform.objects.count() == 5
        assert Platform.objects.values().get(pk=platform_no_source1.pk) == no_source1_values
        assert (
            Platform.objects.get(pk=platform_no_source2.pk).ext_id == PLATFORM_INPUT_DATA2[0]["pk"]
        )
        assert Platform.objects.get(pk=platform_no_source2.pk).counter_registry_id == uuid.UUID(
            PLATFORM_INPUT_DATA2[0]["counter_registry_id"]
        )
        assert Platform.objects.values().get(pk=platform_erms.pk) == erms_values

        platform_with_removed_id.refresh_from_db()
        assert platform_with_removed_id.counter_registry_id is None

    def test_perform(self, data_sources, report_types):
        with requests_mock.Mocker() as m:
            m.get(
                re.compile(f'^{data_sources["brain"].url}.*'), text=json.dumps(PLATFORM_INPUT_DATA)
            )
            attempt1 = PlatformImportAttempt(source=data_sources["brain"])
            attempt1.save()
            attempt1.perform()

            assert m.called
            assert attempt1.url == f'{data_sources["brain"].url}/knowledgebase/platforms/'
            assert attempt1.kind == PlatformImportAttempt.KIND_PLATFORM
            assert attempt1.created_timestamp is not None
            assert attempt1.started_timestamp is not None
            assert attempt1.downloaded_timestamp is not None
            assert attempt1.processing_timestamp is not None
            assert attempt1.end_timestamp is not None
            assert attempt1.data_hash is not None
            assert not attempt1.error

        with requests_mock.Mocker() as m:
            m.get(
                re.compile(f'^{data_sources["brain"].url}.*'), text=json.dumps(PLATFORM_INPUT_DATA)
            )
            attempt2 = PlatformImportAttempt(source=data_sources["brain"])
            attempt2.save()
            attempt2.perform()

            assert m.called
            assert attempt2.url == f'{data_sources["brain"].url}/knowledgebase/platforms/'
            assert attempt2.kind == PlatformImportAttempt.KIND_PLATFORM
            assert attempt2.created_timestamp is not None
            assert attempt2.started_timestamp is not None
            assert attempt2.downloaded_timestamp is not None
            assert attempt2.processing_timestamp is None  # no need to process the same data
            assert attempt2.end_timestamp is not None
            assert attempt2.data_hash == attempt1.data_hash
            assert not attempt2.error

    def test_duplicated_platforms(self, data_sources, report_types):
        PlatformFactory(source=None, short_name="AAP")
        # platform without source, but whith same short name
        platform_with_source = PlatformFactory(
            source=data_sources['brain'], short_name="AAP", ext_id=328, name="XXX"
        )

        with patch('knowledgebase.models.async_mail_admins') as email_task:
            PlatformImportAttempt.objects.create(source=data_sources["brain"]).process(
                PLATFORM_INPUT_DATA, PlatformImportAttempt.MergeStrategy.EMPTY_SOURCE
            )
            assert email_task.delay.called, 'email about duplicated platforms sent'

        platform_with_source.refresh_from_db()
        assert (
            platform_with_source.name == "AAP - American Academy of Pediatrics"
        ), "linked platform updated"


@pytest.mark.django_db
class TestRouterSyncAttempt:
    def test_present_absent(self, organizations):
        DataSourceFactory(
            short_name='first-data-source',
            type=DataSource.TYPE_KNOWLEDGEBASE,
            url='https://first.data.source',
            token="1" * 64,
        )
        DataSourceFactory(
            short_name='second-data-source',
            type=DataSource.TYPE_KNOWLEDGEBASE,
            url='https://second.data.source',
            token="2" * 64,
        )
        # Create two tokens
        OrganizationAPIKeyFactory(organization=organizations["master"])
        token = OrganizationAPIKeyFactory(organization=organizations["branch"])

        assert (
            RouterSyncAttempt.objects.filter(
                target=RouterSyncAttempt.Target.PRESENT, done__isnull=True
            ).count()
            == 4
        ), "Creation of two tokens should create attempts as well"
        assert (
            RouterSyncAttempt.objects.filter(
                target=RouterSyncAttempt.Target.ABSENT, done__isnull=True
            ).count()
            == 0
        ), "Nothing deleted"

        token.delete()

        assert (
            RouterSyncAttempt.objects.filter(
                target=RouterSyncAttempt.Target.PRESENT, done__isnull=True
            ).count()
            == 4
        ), "PRESENT attempts remain the same"
        assert (
            RouterSyncAttempt.objects.filter(
                target=RouterSyncAttempt.Target.ABSENT, done__isnull=True
            ).count()
            == 2
        ), "Deletion of a token should add ABSENT attempt"

    def test_propagete_prefix(self, organizations):
        DataSourceFactory(
            short_name='first-data-source',
            type=DataSource.TYPE_KNOWLEDGEBASE,
            url='https://first.data.source',
            token="1" * 64,
        )
        DataSourceFactory(
            short_name='second-data-source',
            type=DataSource.TYPE_KNOWLEDGEBASE,
            url='https://second.data.source',
            token="2" * 64,
        )


@pytest.mark.django_db
class TestReportTypeImportAttempt:
    def test_process(self, data_sources, report_types, interests):

        # Create
        attempt = ReportTypeImportAttempt(source=data_sources["brain"])
        attempt.save()

        rt_count = ReportType.objects.count()

        attempt.process(REPORT_TYPE_INPUT_DATA)
        assert attempt.stats == {"created": 2, "total": 2}
        assert rt_count + 2 == ReportType.objects.count()

        report_type1 = ReportType.objects.get(short_name="one")
        assert report_type1.name == "first"
        assert report_type1.ext_id == 111
        assert report_type1.controlled_metrics.count() == 0
        assert report_type1.dimensions.count() == 0

        report_type2 = ReportType.objects.get(short_name="two")
        assert report_type2.name == "second"
        assert report_type2.ext_id == 222
        assert report_type2.controlled_metrics.count() == 1
        assert list(report_type2.controlled_metrics.values_list('short_name', flat=True)) == [
            'metric1'
        ]
        assert report_type2.dimensions.count() == 2
        assert list(
            report_type2.reporttypetodimension_set.order_by('position').values_list(
                'position', 'dimension__short_name'
            )
        ) == [(0, 'dim1'), (1, 'dim2')]

        # Create import batch for on of the report types
        ImportBatchFactory(report_type=report_type2)

        rim_count = ReportInterestMetric.objects.count()
        # Update report types agian
        with patch('knowledgebase.models.async_mail_admins') as email_task:
            attempt.process(REPORT_TYPE_INPUT_DATA2)
            assert email_task.delay.called, 'email about inconsistent dimensions sent'

        assert attempt.stats == {"created": 1, "updated": 2, "total": 3}
        assert rt_count + 3 == ReportType.objects.count()
        assert (
            ReportInterestMetric.objects.count() == rim_count + 1
        ), 'report type metric was created'

        report_type1 = ReportType.objects.get(short_name="one")
        assert report_type1.name == "first"
        assert report_type1.ext_id == 111
        assert report_type1.controlled_metrics.count() == 0
        assert report_type1.dimensions.count() == 1
        assert list(
            report_type1.reporttypetodimension_set.order_by('position').values_list(
                'position', 'dimension__short_name'
            )
        ) == [(0, 'dim1')]

        report_type2 = ReportType.objects.get(short_name="Two")
        assert report_type2.name == "SECOND"
        assert report_type2.ext_id == 222
        assert report_type2.controlled_metrics.count() == 1
        assert list(report_type2.controlled_metrics.values_list('short_name', flat=True)) == [
            'metric2'
        ]
        assert report_type2.dimensions.count() == 2
        assert list(
            report_type2.reporttypetodimension_set.order_by('position').values_list(
                'position', 'dimension__short_name'
            )
        ) == [(0, 'dim1'), (1, 'dim2')]

        report_type3 = ReportType.objects.get(short_name="three")
        assert report_type3.name == "third"
        assert report_type3.ext_id == 333
        assert report_type3.controlled_metrics.count() == 2
        assert list(report_type3.controlled_metrics.values_list('short_name', flat=True)) == [
            'metric2',
            'metric3',
        ]
        assert report_type3.dimensions.count() == 2
        assert list(
            report_type3.reporttypetodimension_set.order_by('position').values_list(
                'position', 'dimension__short_name'
            )
        ) == [(0, 'dim4'), (1, 'dim3')]
        assert report_type3.interest_metrics.all().count() == 1
        assert report_type3.interest_metrics.last().short_name == "metric2"
        assert report_type3.reportinterestmetric_set.all().count() == 1
        assert report_type3.reportinterestmetric_set.last().target_metric is None
        assert report_type3.reportinterestmetric_set.last().interest_group.short_name == "search"


@pytest.mark.django_db
class TestParserDefinitionImportAttempt:
    def test_process(
        self, data_sources, parser_definitions, report_types, platforms, metrics, interests
    ):
        def fill_in_nibbler_versions(
            data: dict, lowest: typing.Optional[str] = None, highest: typing.Optional[str] = None
        ):
            data["lowest_nibbler_version"] = lowest or version("celus_nibbler")
            data["highest_nibbler_version"] = highest or version("celus_nibbler")
            return data

        definition = copy.deepcopy(parser_definitions["parser1"].definition)
        definition["pk"] = parser_definitions["parser1"].pk

        attempt = ParserDefinitionImportAttempt(source=data_sources["brain"])
        attempt.save()
        assert not PlatformInterestReport.objects.filter(
            report_type=report_types["custom1"], platform=platforms["brain"]
        ).exists(), "related PlatformInterestReport does not exit"
        attempt.process([fill_in_nibbler_versions(copy.deepcopy(definition))])
        assert attempt.stats == {"same": 1, "total": 1}, "All same"
        assert not PlatformInterestReport.objects.filter(
            report_type=report_types["custom1"], platform=platforms["brain"]
        ).exists(), "PlatformInterestReport was not created"

        definition["parser_name"] = "parserX"
        ReportInterestMetric.objects.create(
            report_type=report_types["custom1"],
            metric=metrics["metric1"],
            interest_group=interests["ig"],
        )
        attempt = ParserDefinitionImportAttempt(source=data_sources["brain"])
        attempt.save()
        attempt.process([fill_in_nibbler_versions(copy.deepcopy(definition))])
        assert attempt.stats == {"updated": 1, "total": 1}, "One updated"
        assert PlatformInterestReport.objects.filter(
            report_type=report_types["custom1"], platform=platforms["brain"]
        ).exists(), "PlatformInterestReport was created"

        definition["pk"] += 1
        definition["parser_name"] = "parserY"
        attempt = ParserDefinitionImportAttempt(source=data_sources["brain"])
        attempt.save()
        attempt.process([fill_in_nibbler_versions(copy.deepcopy(definition))])
        assert attempt.stats == {"created": 1, "total": 1, "wiped": 1}, "One deleted one created"

        attempt = ParserDefinitionImportAttempt(source=data_sources["brain"])
        attempt.save()
        attempt.process([fill_in_nibbler_versions(copy.deepcopy(definition), "1.1.1")])
        assert attempt.stats == {"total": 1, "same": 1}, "lower nibbler version in range"

        attempt = ParserDefinitionImportAttempt(source=data_sources["brain"])
        attempt.save()
        attempt.process([fill_in_nibbler_versions(copy.deepcopy(definition), "1.1.1", "2.2.2")])
        assert attempt.stats == {"total": 1, "wiped": 1}, "nibbler version out of range"
