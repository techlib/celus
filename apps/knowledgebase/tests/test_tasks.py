import copy
import json
import re
from importlib.metadata import version

import pytest
import requests_mock
from knowledgebase.models import ImportAttempt
from logs.models import Metric, ReportInterestMetric, ReportType
from nibbler.models import ParserDefinition
from publications.models import Platform, PlatformInterestReport

from test_fixtures.scenarios.basic import (  # noqa - fixtures
    basic1,
    clients,
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
from . import PLATFORM_INPUT_DATA, REPORT_TYPE_INPUT_DATA2


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

            tasks.sync_all_with_knowledgebase_task()

            assert ImportAttempt.objects.count() == import_attempts + 3
            assert Platform.objects.count() == platform_count + 3
            assert ReportType.objects.count() == report_type_count + 3
            assert ParserDefinition.objects.count() == parser_definition_count + 1
            assert Metric.objects.count() == metric_count + 2
            assert ReportInterestMetric.objects.count() == rim_count + 1
            # 5 report_types with default_platform_interest * 3 new platforms
            # + 1 from parser_definition
            assert PlatformInterestReport.objects.count() == (pir_count + 5 * 3 + 1)
