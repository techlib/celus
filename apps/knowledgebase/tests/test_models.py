import copy
import json
import pytest
import re
import requests_mock

from django.utils.timezone import now
from django.conf import settings

from core.models import DataSource
from knowledgebase.models import PlatformImportAttempt, RouterSyncAttempt
from logs.models import ReportType
from publications.models import Platform

from test_fixtures.scenarios.basic import data_sources, organizations, report_types
from test_fixtures.entities.platforms import PlatformFactory
from test_fixtures.entities.data_souces import DataSourceFactory
from test_fixtures.entities.api import OrganizationAPIKeyFactory


INPUT_DATA = [
    {
        "name": "AAP - American Academy of Pediatrics",
        "pk": 328,
        "provider": "AAP",
        "providers": [
            {
                "assigned_report_types": [
                    {"not_valid_after": None, "not_valid_before": None, "report_type": "JR1"}
                ],
                "counter_version": 4,
                "provider": {
                    "extra": {},
                    "monthly": None,
                    "name": "sushi.highwire.org",
                    "pk": 65,
                    "url": "http://sushi.highwire.org/services/SushiService",
                    "yearly": None,
                },
            },
            {
                "assigned_report_types": [
                    {"not_valid_after": None, "not_valid_before": None, "report_type": "TR"}
                ],
                "counter_version": 5,
                "provider": {
                    "extra": {},
                    "monthly": None,
                    "name": "hwdpapi.highwire.org",
                    "pk": 83,
                    "url": "https://hwdpapi.highwire.org/sushi",
                    "yearly": None,
                },
            },
        ],
        "short_name": "AAP",
        "url": "https://www.aap.org/",
    },
    {
        "name": "American Association for Cancer Research",
        "pk": 327,
        "provider": "AACR",
        "providers": [
            {
                "assigned_report_types": [
                    {"not_valid_after": None, "not_valid_before": None, "report_type": "JR1"}
                ],
                "counter_version": 4,
                "provider": {
                    "extra": {},
                    "monthly": None,
                    "name": "sushi.highwire.org",
                    "pk": 65,
                    "url": "http://sushi.highwire.org/services/SushiService",
                    "yearly": None,
                },
            },
            {
                "assigned_report_types": [
                    {"not_valid_after": None, "not_valid_before": None, "report_type": "TR"}
                ],
                "counter_version": 5,
                "provider": {
                    "extra": {},
                    "monthly": None,
                    "name": "hwdpapi.highwire.org",
                    "pk": 85,
                    "url": "https://hwdpapi.highwire.org/sushi/",
                    "yearly": None,
                },
            },
        ],
        "short_name": "AACR",
        "url": "https://www.aacr.org/",
    },
    {
        "name": "APS",
        "pk": 339,
        "provider": "APS",
        "providers": [],
        "short_name": "APS",
        "url": "https://www.journals.aps.org/",
    },
]

INPUT_DATA2 = [
    {
        "name": "ABC",
        "pk": 340,
        "provider": "ABC",
        "providers": [],
        "short_name": "ABC",
        "url": "https://www.journals.abc.org/",
    },
]


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

        attempt.process(INPUT_DATA)

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
        assert platform1.knowledgebase["providers"] == INPUT_DATA[0]["providers"]
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
        assert platform2.knowledgebase["providers"] == INPUT_DATA[1]["providers"]
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
        assert platform3.knowledgebase["providers"] == []
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
        attempt.process(INPUT_DATA)
        assert attempt.stats == {"same": 3, "total": 3}

        # Update field
        input_data = copy.deepcopy(INPUT_DATA)
        input_data[1]["providers"] = []
        attempt.process(input_data)
        assert attempt.stats == {"updated": 1, "same": 2, "total": 3}

        platform = Platform.objects.get(short_name="AACR")
        assert platform.knowledgebase["providers"] == []

    @pytest.mark.parametrize(
        "strategy,count,no_source,erms",
        (
            (PlatformImportAttempt.MergeStrategy.NONE, 7, False, False),
            (PlatformImportAttempt.MergeStrategy.EMPTY_SOURCE, 6, True, False),
            (PlatformImportAttempt.MergeStrategy.ALL, 5, True, True),
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
        PlatformFactory(short_name="new")
        platform_no_source = PlatformFactory(source=None, short_name="AAP")
        platform_erms = PlatformFactory(source=data_sources["api"], short_name="AACR")
        platform_other_knowledgebase = PlatformFactory(source=other_data_source, short_name="APS")
        other_source = platform_other_knowledgebase.source
        other_ext_id = platform_other_knowledgebase.ext_id

        PlatformImportAttempt.objects.create(source=data_sources["brain"]).process(
            INPUT_DATA, strategy
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

    def test_process_merge_strategies_more_that_one_record(self, data_sources, report_types):

        # Create multiple for ALL strategy
        platform_no_source1 = PlatformFactory(source=None, short_name="AAP")
        no_source1_values = Platform.objects.values().get(pk=platform_no_source1.pk)
        platform_erms = PlatformFactory(source=data_sources["api"], short_name="AAP")
        erms_values = Platform.objects.values().get(pk=platform_erms.pk)

        PlatformImportAttempt.objects.create(source=data_sources["brain"]).process(
            INPUT_DATA, PlatformImportAttempt.MergeStrategy.ALL,
        )
        assert Platform.objects.count() == 4
        assert Platform.objects.values().get(pk=platform_no_source1.pk) == no_source1_values
        assert Platform.objects.values().get(pk=platform_erms.pk) == erms_values

        # Create multiple for EMPTY_SOURCE strategy
        platform_no_source2 = PlatformFactory(source=None, short_name="ABC")
        PlatformImportAttempt.objects.create(source=data_sources["brain"]).process(
            INPUT_DATA2, PlatformImportAttempt.MergeStrategy.EMPTY_SOURCE,
        )
        assert Platform.objects.count() == 5
        assert Platform.objects.values().get(pk=platform_no_source1.pk) == no_source1_values
        assert Platform.objects.get(pk=platform_no_source2.pk).ext_id == INPUT_DATA2[0]["pk"]
        assert Platform.objects.values().get(pk=platform_erms.pk) == erms_values

    def test_perform(self, data_sources, report_types):
        with requests_mock.Mocker() as m:
            m.get(re.compile(f'^{data_sources["brain"].url}.*'), text=json.dumps(INPUT_DATA))
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
            m.get(re.compile(f'^{data_sources["brain"].url}.*'), text=json.dumps(INPUT_DATA))
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


@pytest.mark.django_db
class TestRouterSyncAttempt:
    def test_present_absent(self, organizations):
        ds1 = DataSourceFactory(
            short_name='first-data-source',
            type=DataSource.TYPE_KNOWLEDGEBASE,
            url='https://first.data.source',
            token="1" * 64,
        )
        ds2 = DataSourceFactory(
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
        ds1 = DataSourceFactory(
            short_name='first-data-source',
            type=DataSource.TYPE_KNOWLEDGEBASE,
            url='https://first.data.source',
            token="1" * 64,
        )
        ds2 = DataSourceFactory(
            short_name='second-data-source',
            type=DataSource.TYPE_KNOWLEDGEBASE,
            url='https://second.data.source',
            token="2" * 64,
        )
        pass
