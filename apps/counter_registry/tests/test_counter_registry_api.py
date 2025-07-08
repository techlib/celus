import pytest
from core.models import DataSource
from django.urls import reverse
from publications import fake_data as publications_fake_data
from publications import models as publications_models

from counter_registry.fake_data import PlatformExtrasFactory
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
# we use this in the gitlab pipeline to run these tests using different
# settings
# to run them from the command line, use:
# poetry run pytest --counter-registry apps/counter_registry/tests/
pytestmark = pytest.mark.counter_registry


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
    def test_api_list(self, basic1, clients, users, registry_platform_models, user, status):
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
            assert data[0]["related_platform"] == registry_platform_models["pc"].pk
            assert data[0]["related_platform_provider"] == "PROVIDER"

            assert data[1]["name"] == "Plat2"
            assert data[1]["short_name"] == ""
            assert data[1]["notes"] == "some notes"
            assert (
                data[1]["provider"] == registry_platform_models["p2"].platform.content_provider_name
            )
            assert data[1]["url"] == registry_platform_models["p2"].platform.website
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
    def test_api_patch(self, basic1, clients, users, registry_platform_models, user, status):
        resp = clients[user].patch(
            reverse("counter-platforms-detail", args=(registry_platform_models["p1"].platform.pk,)),
            {"notes": "new_notes"},
        )
        assert resp.status_code == status
        registry_platform_models["p1"].refresh_from_db()
        if status == 200:
            assert registry_platform_models["p1"].notes == "new_notes"
        else:
            assert registry_platform_models["p1"].notes == ""

        # try to unset notes again
        resp = clients[user].patch(
            reverse("counter-platforms-detail", args=(registry_platform_models["p1"].platform.pk,)),
            {"notes": ""},
        )
        assert resp.status_code == status
        registry_platform_models["p1"].refresh_from_db()
        assert registry_platform_models["p1"].notes == ""

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
    def test_api_apply(self, basic1, clients, users, registry_platform_models, user, status):
        updates = {
            "updates": [
                {
                    "id": registry_platform_models["p1"].platform.id,
                    "short_name": True,
                    "url": False,
                    "sushi_services": True,
                },
                {
                    "id": registry_platform_models["p2"].platform.id,
                    "short_name": False,
                    "url": True,
                    "sushi_services": False,
                    "provider": True,
                },
            ]
        }

        old_name = registry_platform_models["pc"].name
        old_short_name = registry_platform_models["pc"].short_name
        old_provider = registry_platform_models["pc"].provider
        old_url = registry_platform_models["pc"].url
        old_knowledgebase = registry_platform_models["pc"].knowledgebase
        old_report_types = set(
            registry_platform_models["pc"].counter_reports.values_list("counter_version", "code")
        )
        old_creds_report_types = set(
            registry_platform_models["creds"].counter_reports.values_list("counter_version", "code")
        )
        old_creds_url = registry_platform_models["creds"].url

        old_platform_count = publications_models.Platform.objects.count()
        resp = clients[user].post(reverse("counter-platforms-apply"), updates, format="json")
        assert resp.status_code == status

        registry_platform_models["p1"].refresh_from_db()
        registry_platform_models["p2"].refresh_from_db()
        registry_platform_models["pc"].refresh_from_db()
        if status == 200:
            # check updated
            assert registry_platform_models["pc"].name == old_name
            assert registry_platform_models["pc"].short_name != old_short_name
            assert registry_platform_models["pc"].url == old_url
            assert registry_platform_models["pc"].provider == old_provider
            assert registry_platform_models["pc"].knowledgebase != old_knowledgebase
            assert (
                set(
                    registry_platform_models["pc"].counter_reports.values_list(
                        "counter_version", "code"
                    )
                )
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

            registry_platform_models["creds"].refresh_from_db()
            assert registry_platform_models["creds"].url == "https://www.example.com/sushi5"
            assert (
                set(
                    registry_platform_models["creds"].counter_reports.values_list(
                        "counter_version", "code"
                    )
                )
                != old_creds_report_types
            )

        else:
            # test that nothing changed
            assert registry_platform_models["pc"].name == old_name
            assert registry_platform_models["pc"].short_name == old_short_name
            assert registry_platform_models["pc"].url == old_url
            assert registry_platform_models["pc"].provider == old_provider
            assert registry_platform_models["pc"].knowledgebase == old_knowledgebase
            assert (
                set(
                    registry_platform_models["pc"].counter_reports.values_list(
                        "counter_version", "code"
                    )
                )
                == old_report_types
            )
            assert publications_models.Platform.objects.count() == old_platform_count

            registry_platform_models["creds"].refresh_from_db()
            assert registry_platform_models["creds"].url == old_creds_url
            assert (
                set(
                    registry_platform_models["creds"].counter_reports.values_list(
                        "counter_version", "code"
                    )
                )
                == old_creds_report_types
            )

        # TODO check pc and creds (should be updated as well)

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
    def test_api_unlinked_platforms(self, basic1, clients, users, user, status):
        # Make sure that no platform exists
        publications_models.Platform.objects.all().delete()

        # Create platforms that should be included in results (no counter_registry_id)
        publications_fake_data.PlatformFactory(
            name="Unlinked Platform 1",
            short_name="UP1",
            provider="Provider1",
            url="https://unlinked1.com",
            counter_registry_id=None,
        )
        publications_fake_data.PlatformFactory(
            name="Unlinked Platform 2",
            short_name="UP2",
            provider="Provider2",
            url="https://unlinked2.com",
            counter_registry_id=None,
        )

        # Create platforms that should be excluded from results

        # 1. Platform with organization data source (excluded)
        org_data_source = DataSource.objects.create(
            short_name="org_source", type=DataSource.TYPE_ORGANIZATION
        )
        publications_fake_data.PlatformFactory(
            name="Org Platform", counter_registry_id=None, source=org_data_source
        )

        # 2. Platform with counter_registry_id (excluded)
        publications_fake_data.PlatformFactory(
            name="Linked Platform", counter_registry_id="f0000000-0000-0000-0000-000000000000"
        )

        resp = clients[user].get(reverse("counter-platforms-unlinked-platforms"))
        assert resp.status_code == status

        if status == 200:
            assert len(resp.data) == 2, "Expected 2 unlinked platforms"
            assert {e["name"] for e in resp.data} == {"Unlinked Platform 1", "Unlinked Platform 2"}

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
    def test_api_link_platforms(self, basic1, clients, users, user, status):
        # create a platform which should be linked
        pc1 = publications_fake_data.PlatformFactory(
            name="Unlinked Platform 1",
            short_name="UP1",
            provider="Provider1",
            url="https://unlinked1.com",
            counter_registry_id=None,
        )
        pc2 = publications_fake_data.PlatformFactory(
            name="Linked Platform 2",
            short_name="LP2",
            provider="Provider2",
            url="https://linked2.com",
            counter_registry_id="f1111111-1111-1111-1111-111111111111",
        )
        pc3 = publications_fake_data.PlatformFactory(
            name="Unlinked Platform 3",
            short_name="UP3",
            provider="Provider3",
            url="https://unlinked3.com",
            counter_registry_id=None,
        )
        pe1 = PlatformExtrasFactory(platform__id="f0000000-0000-0000-0000-000000000000")
        pe2 = PlatformExtrasFactory(platform__id="f2222222-2222-2222-2222-222222222222")
        # Link unlinked platform
        resp = clients[user].post(
            reverse("counter-platforms-link", args=(pe1.platform.id,)), {"platform_id": pc1.pk}
        )
        assert resp.status_code == status
        pc1.refresh_from_db()
        if status == 200:
            assert str(pc1.counter_registry_id) == "f0000000-0000-0000-0000-000000000000"
        else:
            assert pc1.counter_registry_id is None

        # Link platform which is already linked
        resp = clients[user].post(
            reverse("counter-platforms-link", args=(pe2.platform.id,)), {"platform_id": pc2.pk}
        )
        if status == 200:
            assert resp.status_code == 400
        else:
            assert resp.status_code == status
        pc2.refresh_from_db()
        assert str(pc2.counter_registry_id) == "f1111111-1111-1111-1111-111111111111"

        # Reuse same registry_id
        pc1.counter_registry_id = "f0000000-0000-0000-0000-000000000000"
        pc1.save()
        resp = clients[user].post(
            reverse("counter-platforms-link", args=(pe1.platform.id,)), {"platform_id": pc3.pk}
        )
        pc1.refresh_from_db()
        pc3.refresh_from_db()
        if status == 200:
            assert resp.status_code == 404
        else:
            assert resp.status_code == status
        assert str(pc1.counter_registry_id) == "f0000000-0000-0000-0000-000000000000"
        assert pc3.counter_registry_id is None
