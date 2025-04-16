import pytest

try:
    from counter_registry.fake_data import PlatformExtrasFactory, ReportFactory, SushiServiceFactory
    from counter_registry.models import Platform
except ModuleNotFoundError:
    # django_celus_registry is probably not installed
    # we need to deal with this situation otherwise pytest raises an Error
    # while collecting the tests
    pass

from django.urls import reverse
from publications import fake_data as publications_fake_data
from publications import models as publications_models
from sushi import fake_data as sushi_fake_data

from test_scenarios.basic import (  # noqa
    basic1,
    clients,
    counter_report_types,
    data_sources,
    identities,
    organizations,
    platforms,
    report_types,
    users,
)

# mark all tests as with counter_registry
pytestmark = pytest.mark.counter_registry


@pytest.fixture
def registry_models(counter_report_types):
    # make registry models
    jr1 = ReportFactory(counter_release=4, report_id="JR1")
    tr = ReportFactory(counter_release=5, report_id="TR")
    dr = ReportFactory(counter_release=5, report_id="DR")
    ir = ReportFactory(counter_release=51, report_id="IR")
    p1 = PlatformExtrasFactory(
        platform__name="Plat1",
        platform__abbrev="P1",
        platform__content_provider_name="PROVIDER",
        platform__website="https://platform.example.url/",
    )
    p2 = PlatformExtrasFactory(platform__name="Plat2")
    p2.notes = "some notes"  # setting notes via PlatformExtrasFactory doesn't work...
    p2.save()
    SushiServiceFactory(
        platform=p1.platform, counter_release=5, url="https://www.example.com/sushi5"
    )
    SushiServiceFactory(
        platform=p1.platform, counter_release=51, url="https://www.example.com/sushi51"
    )
    SushiServiceFactory(
        platform=p2.platform, counter_release=4, url="https://www.example.com/sushi4"
    )
    p1.platform.reports.add(tr)
    p1.platform.reports.add(dr)
    p1.platform.reports.add(ir)
    p2.platform.reports.add(jr1)
    Platform.objects.all().sync_knowledgebase()
    p1.refresh_from_db()
    p2.refresh_from_db()

    # make celus models
    pc = publications_fake_data.PlatformFactory(
        counter_registry_id=p1.platform.id,
        provider="PROVIDER",
        counter_reports_source="knowledgebase",
    )
    pc.counter_reports.add(counter_report_types["br1"])
    creds = sushi_fake_data.CredentialsFactory(
        counter_version=5, platform=pc, use_counter_reports_from_platform=True, auto_update_url=True
    )
    creds.counter_reports.add(counter_report_types["pr"])

    return locals()


@pytest.mark.django_db
class TestCounterRegistryAPI:
    @pytest.mark.parametrize(
        "user,status",
        (
            ("su", 200),
            ("master_admin", 200),
            ("master_user", 403),
            ("admin1", 403),
            ("admin2", 403),
            ("user1", 403),
            ("user2", 403),
        ),
    )
    def test_api_list(self, basic1, clients, users, registry_models, user, status):
        resp = clients[user].get(reverse("counter-platforms-list"))
        assert resp.status_code == status
        if status == 200:
            assert len(resp.data) == 2
            data = sorted(resp.data, key=lambda e: e["name"])
            assert data[0]["name"] == "Plat1"
            assert data[0]["short_name"] == "P1"
            assert data[0]["notes"] == ""
            assert data[0]["provider"] == "PROVIDER"
            assert data[0]["url"] == "https://platform.example.url/"
            assert data[0]["keep_name"] is False
            assert data[0]["keep_knowledgebase"] is False
            assert data[0]["keep_provider"] is True
            assert data[0]["keep_short_name"] is False
            assert data[0]["keep_url"] is False
            assert data[0]["related_platform"] == registry_models["pc"].pk
            assert data[0]["related_platform_provider"] == "PROVIDER"

            assert data[1]["name"] == "Plat2"
            assert data[1]["short_name"] == ""
            assert data[1]["notes"] == "some notes"
            assert data[1]["provider"] == registry_models["p2"].platform.content_provider_name
            assert data[1]["url"] == registry_models["p2"].platform.website
            assert data[1]["keep_name"] is False
            assert data[1]["keep_knowledgebase"] is False
            assert data[1]["keep_provider"] is False
            assert data[1]["keep_short_name"] is True, "empty url in registry"
            assert data[1]["keep_url"] is False
            assert data[1]["related_platform"] is None
            assert data[1]["related_platform_provider"] is None

    @pytest.mark.parametrize(
        "user,status",
        (
            ("su", 200),
            ("master_admin", 200),
            ("master_user", 403),
            ("admin1", 403),
            ("admin2", 403),
            ("user1", 403),
            ("user2", 403),
        ),
    )
    def test_api_patch(self, basic1, clients, users, registry_models, user, status):
        resp = clients[user].patch(
            reverse("counter-platforms-detail", args=(registry_models["p1"].platform.pk,)),
            {"notes": "new_notes"},
        )
        assert resp.status_code == status
        registry_models["p1"].refresh_from_db()
        if status == 200:
            assert registry_models["p1"].notes == "new_notes"
        else:
            assert registry_models["p1"].notes == ""

        # try to unset notes again
        resp = clients[user].patch(
            reverse("counter-platforms-detail", args=(registry_models["p1"].platform.pk,)),
            {"notes": ""},
        )
        assert resp.status_code == status
        registry_models["p1"].refresh_from_db()
        assert registry_models["p1"].notes == ""

    @pytest.mark.parametrize(
        "user,status",
        (
            ("su", 200),
            ("master_admin", 200),
            ("master_user", 403),
            ("admin1", 403),
            ("admin2", 403),
            ("user1", 403),
            ("user2", 403),
        ),
    )
    def test_api_apply(self, basic1, clients, users, registry_models, user, status):
        updates = {
            "updates": [
                {
                    "id": registry_models["p1"].platform.id,
                    "short_name": True,
                    "url": False,
                    "sushi_services": True,
                },
                {
                    "id": registry_models["p2"].platform.id,
                    "short_name": False,
                    "url": True,
                    "sushi_services": False,
                    "provider": True,
                },
            ]
        }

        old_name = registry_models["pc"].name
        old_short_name = registry_models["pc"].short_name
        old_provider = registry_models["pc"].provider
        old_url = registry_models["pc"].url
        old_knowledgebase = registry_models["pc"].knowledgebase
        old_report_types = set(
            registry_models["pc"].counter_reports.values_list("counter_version", "code")
        )
        old_creds_report_types = set(
            registry_models["creds"].counter_reports.values_list("counter_version", "code")
        )
        old_creds_url = registry_models["creds"].url

        old_platform_count = publications_models.Platform.objects.count()
        resp = clients[user].post(reverse("counter-platforms-apply"), updates, format="json")
        assert resp.status_code == status

        registry_models["p1"].refresh_from_db()
        registry_models["p2"].refresh_from_db()
        registry_models["pc"].refresh_from_db()
        if status == 200:
            # check updated
            assert registry_models["pc"].name == old_name
            assert registry_models["pc"].short_name != old_short_name
            assert registry_models["pc"].url == old_url
            assert registry_models["pc"].provider == old_provider
            assert registry_models["pc"].knowledgebase != old_knowledgebase
            assert (
                set(registry_models["pc"].counter_reports.values_list("counter_version", "code"))
                != old_report_types
            )

            assert publications_models.Platform.objects.count() == old_platform_count + 1
            new_platform = publications_models.Platform.objects.order_by("pk").last()
            assert new_platform.name == "Plat2"
            assert new_platform.short_name == "Plat2", "no abbrev present => use name"
            assert new_platform.provider == ""
            assert new_platform.url == "https://example.com", "default fallback"
            assert new_platform.knowledgebase["providers"][0]["assigned_report_types"] == [
                {"not_valid_after": None, "not_valid_before": None, "report_type": "JR1"}
            ]
            assert new_platform.knowledgebase["providers"][0]["counter_version"] == 4
            assert (
                new_platform.knowledgebase["providers"][0]["provider"]["url"]
                == "https://www.example.com/sushi4"
            )

            registry_models["creds"].refresh_from_db()
            assert registry_models["creds"].url == "https://www.example.com/sushi5"
            assert (
                set(registry_models["creds"].counter_reports.values_list("counter_version", "code"))
                != old_creds_report_types
            )

        else:
            # test that nothing changed
            assert registry_models["pc"].name == old_name
            assert registry_models["pc"].short_name == old_short_name
            assert registry_models["pc"].url == old_url
            assert registry_models["pc"].provider == old_provider
            assert registry_models["pc"].knowledgebase == old_knowledgebase
            assert (
                set(registry_models["pc"].counter_reports.values_list("counter_version", "code"))
                == old_report_types
            )
            assert publications_models.Platform.objects.count() == old_platform_count

            registry_models["creds"].refresh_from_db()
            assert registry_models["creds"].url == old_creds_url
            assert (
                set(registry_models["creds"].counter_reports.values_list("counter_version", "code"))
                == old_creds_report_types
            )

        # TODO check pc and creds (should be updated as well)
