import csv
import tempfile

import pytest

from counter_registry.models import Platform, PlatformExtras


@pytest.fixture(
    params=["88888888-8888-8888-8888-888888888888", "99999999-9999-9999-9999-999999999999"]
)
def csv_override_file(request):
    with tempfile.NamedTemporaryFile("w", suffix=".csv", newline="") as file:
        writer = csv.DictWriter(
            file,
            ["id", "name", "registry_id", "sushi_host", "status", "counter_version", "report_code"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "id": "",
                "name": "Plat1",
                "registry_id": request.param,
                "sushi_host": "Provider1",
                "status": "MATCH",
                "counter_version": "5.1",
                "report_code": "IR",
            }
        )

        file.flush()
        yield file.name, request.param


@pytest.mark.django_db
class TestWhitelisted:
    def test_no_whitelist(self, registry_platform_models):
        PlatformExtras.objects.update(knowledgebase={})

        registry_platform_models["p1"].refresh_from_db()
        registry_platform_models["p2"].refresh_from_db()

        assert registry_platform_models["p1"].knowledgebase == {}
        assert registry_platform_models["p2"].knowledgebase == {}

        Platform.objects.all().sync_knowledgebase()

        registry_platform_models["p1"].refresh_from_db()
        registry_platform_models["p2"].refresh_from_db()

        assert registry_platform_models["p1"].knowledgebase["providers"][0][
            "assigned_report_types"
        ] == [
            {
                "not_valid_after": None,
                "not_valid_before": None,
                "report_type": "DR",
                "whitelisted": True,
            },
            {
                "not_valid_after": None,
                "not_valid_before": None,
                "report_type": "TR",
                "whitelisted": True,
            },
        ]
        assert registry_platform_models["p1"].knowledgebase["providers"][1][
            "assigned_report_types"
        ] == [
            {
                "not_valid_after": None,
                "not_valid_before": None,
                "report_type": "IR",
                "whitelisted": False,
            }
        ]
        assert registry_platform_models["p2"].knowledgebase["providers"][0][
            "assigned_report_types"
        ] == [
            {
                "not_valid_after": None,
                "not_valid_before": None,
                "report_type": "JR1",
                "whitelisted": True,
            }
        ]

    def test_whitelist(self, settings, registry_platform_models, csv_override_file):
        settings.WHITELISTED_OVERRIDE_CSV_PATH = csv_override_file[0]
        PlatformExtras.objects.update(knowledgebase={})

        registry_platform_models["p1"].refresh_from_db()
        registry_platform_models["p2"].refresh_from_db()

        assert registry_platform_models["p1"].knowledgebase == {}
        assert registry_platform_models["p2"].knowledgebase == {}

        Platform.objects.all().sync_knowledgebase()

        registry_platform_models["p1"].refresh_from_db()
        registry_platform_models["p2"].refresh_from_db()

        assert registry_platform_models["p1"].knowledgebase["providers"][0][
            "assigned_report_types"
        ] == [
            {
                "not_valid_after": None,
                "not_valid_before": None,
                "report_type": "DR",
                "whitelisted": True,
            },
            {
                "not_valid_after": None,
                "not_valid_before": None,
                "report_type": "TR",
                "whitelisted": True,
            },
        ]
        assert registry_platform_models["p1"].knowledgebase["providers"][1][
            "assigned_report_types"
        ] == [
            {
                "not_valid_after": None,
                "not_valid_before": None,
                "report_type": "IR",
                "whitelisted": csv_override_file[1] == "88888888-8888-8888-8888-888888888888",
            }
        ]
        assert registry_platform_models["p2"].knowledgebase["providers"][0][
            "assigned_report_types"
        ] == [
            {
                "not_valid_after": None,
                "not_valid_before": None,
                "report_type": "JR1",
                "whitelisted": True,
            }
        ]
