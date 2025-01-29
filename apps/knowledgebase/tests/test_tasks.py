import copy
import json
import re
from importlib.metadata import version
from unittest.mock import patch

import pytest
import requests_mock
from logs.models import Dimension, Metric, ReportInterestMetric, ReportType
from nibbler.models import ParserDefinition
from publications.fake_data import PlatformFactory
from publications.models import Platform, PlatformInterestReport
from sushi.fake_data import FetchAttemptFactory
from sushi.models import AttemptStatus

from knowledgebase.models import ImportAttempt
from test_scenarios.basic import (  # noqa - fixtures
    basic1,
    clients,
    counter_report_types,
    data_sources,
    interests,
    metrics,
    organizations,
    parser_definitions,
    platforms,
    report_types,
    users,
)

from .. import tasks
from . import PLATFORM_INPUT_DATA, PLATFORM_INPUT_DATA3, REPORT_TYPE_INPUT_DATA2


@pytest.mark.django_db
class TestCeleryTasks:
    def test_sync_knowledgebase_task(self, data_sources, parser_definitions, interests):
        """This test should trigger all knowledgebase sync tasks"""

        with requests_mock.Mocker() as m:
            m.get(
                re.compile(f'^{data_sources["brain"].url}/knowledgebase/platforms/'),
                text=json.dumps(PLATFORM_INPUT_DATA),
            )
            m.get(
                re.compile(f'^{data_sources["brain"].url}/knowledgebase/report_types/'),
                text=json.dumps(REPORT_TYPE_INPUT_DATA2),
            )

            definition = copy.deepcopy(parser_definitions["parser1"].definition)
            definition["pk"] = parser_definitions["parser1"].pk + 1
            definition["parser_name"] = "task_sync"
            definition["data_format"]["name"] = "three"
            definition["data_format"]["id"] = 333
            definition["lowest_nibbler_version"] = version("celus_nibbler")
            m.get(
                re.compile(f'^{data_sources["brain"].url}/knowledgebase/report_types/'),
                text=json.dumps(REPORT_TYPE_INPUT_DATA2),
            )
            definition["highest_nibbler_version"] = version("celus_nibbler")
            definition["platforms"] = ["APS"]
            parser_definitions["parser1"].delete()

            m.get(
                re.compile(f'^{data_sources["brain"].url}/knowledgebase/parsers/'),
                text=json.dumps([definition]),
            )

            platform_count = Platform.objects.count()
            report_type_count = ReportType.objects.count()
            parser_definition_count = ParserDefinition.objects.count()
            import_attempts = ImportAttempt.objects.count()
            rim_count = ReportInterestMetric.objects.count()
            pir_count = PlatformInterestReport.objects.count()
            metric_count = Metric.objects.count()

            # Create some dimensions
            Dimension.objects.create(short_name="dim1")
            Dimension.objects.create(short_name="dim2")

            dimension_count = Dimension.objects.count()

            tasks.sync_all_with_knowledgebase_task()

            assert ImportAttempt.objects.count() == import_attempts + 3
            assert Platform.objects.count() == platform_count + 3
            assert ReportType.objects.count() == report_type_count + 3
            assert ParserDefinition.objects.count() == parser_definition_count + 1
            assert Metric.objects.count() == metric_count, "no new metrics should be created"
            assert ReportInterestMetric.objects.count() == rim_count + 3
            # 7 report_types with default_platform_interest * 3 new platforms
            # + 1 from parser_definition
            assert PlatformInterestReport.objects.count() == (pir_count + 7 * 3 + 1)

            # The REPORT_TYPE_INPUT_DATA2 contains 3 dimensions
            # 1 was created before the sync and 2 were created during the sync
            assert dimension_count + 2 == Dimension.objects.count(), "two dimensions were created"

    def test_sync_knowledgebase_fail_task(self, data_sources):
        with requests_mock.Mocker() as m:
            m.get(
                re.compile(f'^{data_sources["brain"].url}/knowledgebase/platforms/'),
                text=json.dumps({"wrong": "format"}),
            )

            m.get(
                re.compile(f'^{data_sources["brain"].url}/knowledgebase/report_types/'),
                text=json.dumps({"wrong": "format"}),
            )
            m.get(
                re.compile(f'^{data_sources["brain"].url}/knowledgebase/parsers/'),
                text=json.dumps({"wrong": "format"}),
            )

            with patch("knowledgebase.tasks.async_mail_admins") as email_task:
                tasks.sync_all_with_knowledgebase_task()
                assert email_task.delay.called

            with patch("knowledgebase.tasks.async_mail_admins") as email_task:
                tasks.sync_report_types_with_knowledgebase_task()
                assert email_task.delay.called

            with patch("knowledgebase.tasks.async_mail_admins") as email_task:
                tasks.sync_parser_definitions_with_knowledgebase_task()
                assert email_task.delay.called

            with patch("knowledgebase.tasks.async_mail_admins") as email_task:
                tasks.sync_platforms_with_knowledgebase_task()
                assert email_task.delay.called

    def test_export_data_sync(
        self, data_sources, parser_definitions, interests, settings, counter_report_types
    ):
        settings.KNOWLEDGEBASE_EXPORT_DATA = True
        settings.FAKE_SUSHI_URLS = ["https://fake.example.com/"]
        platform = PlatformFactory(
            short_name="fake", name="fake", ext_id=8888, source=data_sources["brain"]
        )
        FetchAttemptFactory(
            credentials__counter_version=5,
            credentials__platform=platform,
            counter_report=counter_report_types["tr"],
            used_url="https://sushi.example.com/reports/tr/",
        )
        FetchAttemptFactory(
            credentials__counter_version=5,
            credentials__platform=platform,
            counter_report=counter_report_types["dr"],
            used_url="https://sushi.example.com/reports/dr/",
        )
        FetchAttemptFactory(
            credentials__counter_version=5,
            credentials__platform=platform,
            counter_report=counter_report_types["pr"],
            used_url="https://fake.example.com/",
        )
        FetchAttemptFactory(
            credentials__counter_version=5,
            credentials__platform=platform,
            counter_report=counter_report_types["pr"],
            used_url="https://sushi.example.com/reports/pr/",
            status=AttemptStatus.PARSING_FAILED,
        )
        FetchAttemptFactory(
            credentials__counter_version=51,
            credentials__platform=platform,
            counter_report=counter_report_types["ir51"],
            used_url="https://sushi.example.com/reports/ir/",
        )
        FetchAttemptFactory(
            credentials__counter_version=51,
            credentials__platform=platform,
            counter_report=counter_report_types["tr51"],
            used_url="",
        )
        with requests_mock.Mocker() as m:
            m.post(
                re.compile(
                    f'^{data_sources["brain"].url}/knowledgebase/platforms/update-assigned-report-types/'
                ),
                text=json.dumps(PLATFORM_INPUT_DATA3),
            )
            tasks.sync_platforms_with_knowledgebase_task()
            assert m.last_request.json() == [
                {
                    "counter_report_code": "TR",
                    "platform_id": 8888,
                    "counter_version": 5,
                    "urls": ["https://sushi.example.com/reports/tr/"],
                },
                {
                    "counter_report_code": "DR",
                    "platform_id": 8888,
                    "counter_version": 5,
                    "urls": ["https://sushi.example.com/reports/dr/"],
                },
                {
                    "counter_report_code": "IR",
                    "platform_id": 8888,
                    "counter_version": 51,
                    "urls": ["https://sushi.example.com/reports/ir/"],
                },
            ], "Post data matches"
        assert Platform.objects.filter(ext_id=328).exists(), "Platform was created"
