import copy
import json
import pytest
import re
import requests_mock

from django.utils.timezone import now
from django.conf import settings

from core.models import DataSource
from knowledgebase.models import PlatformImportAttempt
from publications.models import Platform

from test_fixtures.scenarios.basic import data_sources, organizations


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

    def test_process(self, data_sources):

        attempt = PlatformImportAttempt(source=data_sources["brain"])
        attempt.save()

        attempt.process(INPUT_DATA)

        # Check update
        assert attempt.stats == {"created": 3, "total": 3}

        # Check created platforms
        platform1 = Platform.objects.get(short_name="AAP")
        assert platform1.url == "https://www.aap.org/"
        assert platform1.provider == "AAP"
        assert platform1.name == "AAP - American Academy of Pediatrics"
        assert platform1.ext_id == 328
        assert platform1.knowledgebase["providers"] == INPUT_DATA[0]["providers"]

        platform2 = Platform.objects.get(short_name="AACR")
        assert platform2.url == "https://www.aacr.org/"
        assert platform2.provider == "AACR"
        assert platform2.name == "American Association for Cancer Research"
        assert platform2.ext_id == 327
        assert platform2.knowledgebase["providers"] == INPUT_DATA[1]["providers"]

        platform3 = Platform.objects.get(short_name="APS")
        assert platform3.url == "https://www.journals.aps.org/"
        assert platform3.provider == "APS"
        assert platform3.name == "APS"
        assert platform3.ext_id == 339
        assert platform3.knowledgebase["providers"] == []

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

    def test_perform(self, data_sources):
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
