import copy
import json
import re
import typing
import uuid
from importlib.metadata import version
from unittest.mock import patch

import pytest
import requests_mock
from api.fake_data import OrganizationAPIKeyFactory
from core.fake_data import DataSourceFactory
from core.models import DataSource
from django.utils.timezone import now
from freezegun import freeze_time
from logs.fake_data import ImportBatchFactory, MetricFactory
from logs.models import Dimension, Metric, ReportInterestMetric, ReportType
from publications.fake_data import PlatformFactory
from publications.logic import knowledgebase
from publications.models import Platform
from scheduler.models import FetchIntention
from sushi.fake_data import CredentialsFactory, FetchAttemptFactory
from sushi.models import AttemptStatus, CounterReportPlatform, SushiCredentials

from knowledgebase.models import (
    ParserDefinitionImportAttempt,
    PlatformImportAttempt,
    ReportTypeImportAttempt,
    RouterSyncAttempt,
)
from test_scenarios.basic import (  # noqa - fixtures
    counter_report_types,
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
    PLATFORM_INPUT_DATA3,
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
                "error occured",
                "a" * 64,
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
                "a" * 64,
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
                "a" * 64,
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
                "a" * 64,
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
                "a" * 64,
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
        assert platform1.knowledgebase["notes_url"] is None

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
        assert platform2.knowledgebase["notes_url"] == PLATFORM_INPUT_DATA[1]["notes_url"]

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
        assert platform3.knowledgebase["notes_url"] is None

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

        # Update one platform to C5.1 and add a new C5 platform
        PlatformImportAttempt.objects.create(source=data_sources["brain"]).process(
            PLATFORM_INPUT_DATA3, PlatformImportAttempt.MergeStrategy.EMPTY_SOURCE
        )
        assert Platform.objects.count() == 6
        updated_platform = Platform.objects.get(ext_id=PLATFORM_INPUT_DATA3[0]["pk"])
        assert updated_platform.knowledgebase["providers"][0]["counter_version"] == 51
        assert (
            updated_platform.knowledgebase["providers"][0]["assigned_report_types"][0][
                "report_type"
            ]
            == "TR51"
        )

        new_platform = Platform.objects.get(ext_id=PLATFORM_INPUT_DATA3[1]["pk"])
        assert new_platform.knowledgebase["providers"][0]["counter_version"] == 51
        assert (
            new_platform.knowledgebase["providers"][0]["assigned_report_types"][0]["report_type"]
            == "TR51"
        )

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
            source=data_sources["brain"], short_name="AAP", ext_id=328, name="XXX"
        )

        with patch("knowledgebase.models.async_mail_admins") as email_task:
            PlatformImportAttempt.objects.create(source=data_sources["brain"]).process(
                PLATFORM_INPUT_DATA, PlatformImportAttempt.MergeStrategy.EMPTY_SOURCE
            )
            assert email_task.delay.called, "email about duplicated platforms sent"

        platform_with_source.refresh_from_db()
        assert (
            platform_with_source.name == "AAP - American Academy of Pediatrics"
        ), "linked platform updated"

    @freeze_time("2020-01-15 00:00:00")
    @pytest.mark.parametrize("verification", ("forced", "attempt"))
    def test_process_credentials_update(
        self, data_sources, report_types, counter_report_types, verification, organizations
    ):
        org = organizations["standalone"]
        p1 = PlatformFactory(short_name="AAP", ext_id=328, source=data_sources["brain"])
        p2 = PlatformFactory(short_name="AACR", ext_id=327, source=data_sources["brain"])
        # auto + enabled + verfied
        cred1 = CredentialsFactory(
            platform=p1,
            url="https://something.else1",
            counter_version=5,
            auto_update_url=True,
            organization=org,
            enabled=True,
            report_types=[(5, "TR")],
        )
        if verification == "forced":
            cred1.force_current_version_verified()
        elif verification == "attempt":
            FetchAttemptFactory(
                credentials=cred1,
                status=AttemptStatus.SUCCESS,
                credentials_version_hash=cred1.version_hash,
            )

        # auto + enabled
        cred2 = CredentialsFactory(
            platform=p2,
            url="https://something.else2",
            counter_version=4,
            auto_update_url=True,
            organization=org,
            enabled=True,
            report_types=[(4, "JR1")],
        )

        # auto + verified
        cred3 = CredentialsFactory(
            platform=p2,
            url="https://something.else3",
            counter_version=5,
            auto_update_url=True,
            organization=org,
            enabled=False,
            report_types=[(5, "DR")],
        )
        cred3.force_current_version_verified()

        # Create ib for one of the platforms
        # => should not create intention for the period
        ImportBatchFactory(
            date="2019-12-01", organization=org, platform=p1, report_type=report_types["tr"]
        )

        attempt = PlatformImportAttempt(source=data_sources["brain"])
        attempt.save()

        assert FetchIntention.objects.count() == 0, "No intention exists so far"

        attempt.process(PLATFORM_INPUT_DATA)

        p1.refresh_from_db()
        p2.refresh_from_db()

        # We need to discard cached_properties so we need to refetch the objects again
        cred1 = SushiCredentials.objects.get(pk=cred1.pk)
        cred2 = SushiCredentials.objects.get(pk=cred2.pk)
        cred3 = SushiCredentials.objects.get(pk=cred3.pk)

        # Both knowledgebase url were updated
        assert (
            cred1.url
            == cred1.knowledgebase_url
            == knowledgebase.get_url(cred1.platform.knowledgebase, cred1.counter_version)
            == PLATFORM_INPUT_DATA[0]["providers"][1]["provider"]["url"]
        )
        assert (
            cred2.url
            == cred2.knowledgebase_url
            == knowledgebase.get_url(cred2.platform.knowledgebase, cred2.counter_version)
            == PLATFORM_INPUT_DATA[1]["providers"][0]["provider"]["url"]
        )
        assert (
            cred3.url
            == cred3.knowledgebase_url
            == knowledgebase.get_url(cred3.platform.knowledgebase, cred3.counter_version)
            == PLATFORM_INPUT_DATA[1]["providers"][1]["provider"]["url"]
        )

        assert cred1.is_verified is True, "Credentials must remain verified"
        assert cred2.is_verified is False, "Credentials must remain unverified"
        assert cred3.is_verified is True, "Credentials must remain verified"

        assert FetchIntention.objects.count() == 1, "Intention created"
        assert FetchIntention.objects.last().start_date.strftime("%Y-%m-%d") == "2019-11-01"

    @pytest.mark.parametrize(
        "counter_reports_source,use_counter_reports_from_platform,platform_updated,creds_updated",
        (
            ("knowledgebase", True, True, True),
            ("knowledgebase", False, True, False),
            ("manual", True, False, False),
            ("manual", False, False, False),
        ),
    )
    def test_process_credentials_update(
        self,
        data_sources,
        report_types,
        counter_report_types,
        organizations,
        counter_reports_source,
        use_counter_reports_from_platform,
        platform_updated,
        creds_updated,
    ):
        p1 = PlatformFactory(
            short_name="AAP",
            ext_id=328,
            source=data_sources["brain"],
            counter_reports_source=counter_reports_source,
        )
        CounterReportPlatform.objects.create(platform=p1, counter_report=counter_report_types["ir"])
        p2 = PlatformFactory(
            short_name="AACR",
            ext_id=327,
            source=data_sources["brain"],
            counter_reports_source="manual",
        )
        CounterReportPlatform.objects.create(platform=p2, counter_report=counter_report_types["ir"])
        p3 = PlatformFactory(
            short_name="APS",
            ext_id=339,
            source=data_sources["brain"],
            counter_reports_source="knowledgebase",
        )
        CounterReportPlatform.objects.create(platform=p3, counter_report=counter_report_types["ir"])

        creds_affected = CredentialsFactory(
            platform=p1,
            url="https://something.else1",
            counter_version=5,
            use_counter_reports_from_platform=use_counter_reports_from_platform,
            organization=organizations["standalone"],
            enabled=True,
        )
        creds_affected.counter_reports.add(counter_report_types["dr"])

        creds_manual = CredentialsFactory(
            platform=p1,
            url="https://something.else2",
            counter_version=5,
            use_counter_reports_from_platform=False,
            organization=organizations["branch"],
            enabled=True,
        )
        creds_manual.counter_reports.add(counter_report_types["pr"])

        creds_empty = CredentialsFactory(
            platform=p1,
            url="https://something.else2",
            counter_version=51,
            use_counter_reports_from_platform=True,
            organization=organizations["branch"],
            enabled=True,
        )
        creds_empty.counter_reports.add(counter_report_types["tr51"])

        attempt = PlatformImportAttempt(source=data_sources["brain"])
        attempt.save()
        attempt.process(PLATFORM_INPUT_DATA)

        p1.refresh_from_db()
        p2.refresh_from_db()
        p3.refresh_from_db()

        if platform_updated:
            assert set(p1.counter_reports.values_list("counter_version", "code")) == {
                (5, "TR"),
                (4, "JR1"),
            }
        else:
            assert set(p1.counter_reports.values_list("counter_version", "code")) == {(5, "IR")}
        assert set(p2.counter_reports.values_list("counter_version", "code")) == {(5, "IR")}
        assert set(p3.counter_reports.values_list("counter_version", "code")) == set()

        if creds_updated:
            assert set(creds_affected.counter_reports.values_list("counter_version", "code")) == {
                (5, "TR")
            }
        else:
            # affected credentials can be either
            # IR - if platform report types were not synced
            # or DR when it were synced
            assert set(
                creds_affected.counter_reports.values_list("counter_version", "code")
            ).issubset({(5, "DR"), (5, "IR")})
        assert set(creds_manual.counter_reports.values_list("counter_version", "code")) == {
            (5, "PR")
        }
        assert set(creds_empty.counter_reports.values_list("counter_version", "code")) == set()


@pytest.mark.django_db
class TestRouterSyncAttempt:
    def test_present_absent(self, organizations):
        DataSourceFactory(
            short_name="first-data-source",
            type=DataSource.TYPE_KNOWLEDGEBASE,
            url="https://first.data.source",
            token="1" * 64,
        )
        DataSourceFactory(
            short_name="second-data-source",
            type=DataSource.TYPE_KNOWLEDGEBASE,
            url="https://second.data.source",
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

    def test_propagate_prefix(self, organizations):
        DataSourceFactory(
            short_name="first-data-source",
            type=DataSource.TYPE_KNOWLEDGEBASE,
            url="https://first.data.source",
            token="1" * 64,
        )
        DataSourceFactory(
            short_name="second-data-source",
            type=DataSource.TYPE_KNOWLEDGEBASE,
            url="https://second.data.source",
            token="2" * 64,
        )

    def test_get_token_from_settings(self, settings):
        settings.KNOWLEDGEBASE_TOKEN = "1" * 64
        src = DataSourceFactory(
            short_name="kb",
            type=DataSource.TYPE_KNOWLEDGEBASE,
            url="https://second.data.source",
            token="$",
        )
        with requests_mock.Mocker() as m:
            m.get(re.compile(f"^{src.url}.*"), text="{}")
            attempt1 = PlatformImportAttempt(source=src)
            attempt1.save()
            attempt1.perform()

            assert m.called
            assert (
                m.last_request.headers["Authorization"] == f"Token {settings.KNOWLEDGEBASE_TOKEN}"
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
        assert report_type2.controlled_metrics.count() == 3
        assert set(report_type2.controlled_metrics.values_list("short_name", flat=True)) == {
            "metric1",
            "metric2",
            "metric3",
        }
        assert report_type2.dimensions.count() == 2
        assert list(
            report_type2.reporttypetodimension_set.order_by("position").values_list(
                "position", "dimension__short_name"
            )
        ) == [(0, "dim1"), (1, "dim2")]
        assert list(
            report_type2.reportinterestmetric_set.order_by("id").values_list(
                "metric__short_name", "interest_group__short_name"
            )
        ) == [("metric1", "multimedia"), ("metric2", "search"), ("metric3", "other")]

        # Create import batch for on of the report types
        ImportBatchFactory(report_type=report_type2)

        rim_count = ReportInterestMetric.objects.count()
        # Update report types agian
        with patch("knowledgebase.models.async_mail_admins") as email_task:
            attempt.process(REPORT_TYPE_INPUT_DATA2)
            assert email_task.delay.called, "email about inconsistent dimensions sent"

        assert attempt.stats == {"created": 1, "updated": 2, "total": 3}
        assert rt_count + 3 == ReportType.objects.count()
        assert (
            ReportInterestMetric.objects.count() == rim_count
        ), "two report type metric were created and two were delete"

        report_type1 = ReportType.objects.get(short_name="one")
        assert report_type1.name == "first"
        assert report_type1.ext_id == 111
        assert report_type1.controlled_metrics.count() == 0
        assert report_type1.dimensions.count() == 1
        assert list(
            report_type1.reporttypetodimension_set.order_by("position").values_list(
                "position", "dimension__short_name"
            )
        ) == [(0, "dim1")]

        report_type2 = ReportType.objects.get(short_name="Two")
        assert report_type2.name == "SECOND"
        assert report_type2.ext_id == 222
        assert report_type2.controlled_metrics.count() == 2
        assert list(
            report_type2.controlled_metrics.order_by("short_name").values_list(
                "short_name", flat=True
            )
        ) == ["metric2", "metric3"]
        assert report_type2.dimensions.count() == 2
        assert list(
            report_type2.reporttypetodimension_set.order_by("position").values_list(
                "position", "dimension__short_name"
            )
        ) == [(0, "dim1"), (1, "dim2")]
        assert list(
            report_type2.reportinterestmetric_set.order_by("id").values_list(
                "metric__short_name", "interest_group__short_name"
            )
        ) == [("metric3", "search")]

        report_type3 = ReportType.objects.get(short_name="three")
        assert report_type3.name == "third"
        assert report_type3.ext_id == 333
        assert report_type3.controlled_metrics.count() == 2
        assert list(report_type3.controlled_metrics.values_list("short_name", flat=True)) == [
            "metric2",
            "metric3",
        ]
        assert report_type3.dimensions.count() == 2
        assert list(
            report_type3.reporttypetodimension_set.order_by("position").values_list(
                "position", "dimension__short_name"
            )
        ) == [(0, "dim4"), (1, "dim3")]
        assert report_type3.interest_metrics.all().count() == 2
        assert report_type3.interest_metrics.order_by("id").first().short_name == "metric2"
        assert report_type3.interest_metrics.order_by("id").last().short_name == "metric3"
        assert report_type3.reportinterestmetric_set.all().count() == 2
        assert (
            report_type3.reportinterestmetric_set.order_by("id").first().interest_group.short_name
            == "search"
        )
        assert (
            report_type3.reportinterestmetric_set.order_by("id").last().interest_group.short_name
            == "other"
        )

    def test_metrics_are_not_duplicated(self, data_sources):
        MetricFactory(short_name="metric1", source=None)
        MetricFactory(short_name="metric2", source=None)
        MetricFactory(short_name="metric3", source=None)
        assert Metric.objects.count() == 3
        attempt = ReportTypeImportAttempt(source=data_sources["brain"])
        attempt.save()
        attempt.process(REPORT_TYPE_INPUT_DATA)  # contains the `metric1` metric
        assert Metric.objects.count() == 3, "metric were not duplicated"
        assert Metric.objects.filter(short_name="metric1").first().source is None

    def test_metrics_do_not_use_brain_source(self, data_sources):
        assert Metric.objects.count() == 0
        attempt = ReportTypeImportAttempt(source=data_sources["brain"])
        attempt.save()
        attempt.process(REPORT_TYPE_INPUT_DATA)  # contains the `metric1` metric
        assert Metric.objects.count() == 3, "metrics were created"
        assert Metric.objects.filter(short_name="metric1").first().source is None

    def test_dimensions_do_not_use_brain_source(self, data_sources):
        orig_count = Dimension.objects.count()
        attempt = ReportTypeImportAttempt(source=data_sources["brain"])
        attempt.save()
        attempt.process(REPORT_TYPE_INPUT_DATA)  # contains 2 new dimensions
        assert Dimension.objects.count() == 2 + orig_count, "2 dimensions were created"


@pytest.mark.django_db
class TestParserDefinitionImportAttempt:
    def test_process(
        self,
        data_sources,
        parser_definitions,
        report_types,
        platforms,
        metrics,
        interests,
        settings,
    ):
        settings.DISABLE_NIBBLER_PARSER_VERSION_CHECK = False

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
        attempt.process([fill_in_nibbler_versions(copy.deepcopy(definition))])
        assert attempt.stats == {"same": 1, "total": 1}, "All same"

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

        settings.DISABLE_NIBBLER_PARSER_VERSION_CHECK = True
        attempt = ParserDefinitionImportAttempt(source=data_sources["brain"])
        attempt.save()
        attempt.process([fill_in_nibbler_versions(copy.deepcopy(definition), "1.1.1", "2.2.2")])
        assert attempt.stats == {"total": 1, "created": 1}, "version checks were disabled"
