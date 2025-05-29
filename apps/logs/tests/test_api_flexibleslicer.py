import pytest
from core.logic.serialization import b64json
from django.urls import reverse
from organizations.models import UserOrganization
from publications.fake_data import PlatformFactory
from publications.tests.conftest import interest_rt  # noqa - fixture
from sushi.fake_data import CredentialsFactory
from tags.fake_data import TagFactory
from tags.models import TagScope, TitleTag

from logs.models import ImportBatch, OrganizationPlatform, ReportType
from test_scenarios.basic import (  # noqa
    clients,
    counter_report_types,
    data_sources,
    identities,
    organizations,
    report_types,
    users,
)


@pytest.mark.django_db
class TestSlicerAPI:
    def test_primary_dimension_required(self, flexible_slicer_test_data, admin_client):
        url = reverse("flexible-slicer")
        resp = admin_client.get(url)
        assert resp.status_code == 400
        assert "error" in resp.json()
        assert resp.json()["error"]["code"] == "E104"

    def test_group_by_required(self, flexible_slicer_test_data, admin_client):
        url = reverse("flexible-slicer")
        resp = admin_client.get(url, {"primary_dimension": "platform"})
        assert resp.status_code == 400
        assert "error" in resp.json()
        assert resp.json()["error"]["code"] == "E106"

    def test_user_organization_filtering_no_access(self, flexible_slicer_test_data, users, client):
        """
        Test that organizations in reporting API are properly filtered to only contain those
        accessible by current user.
        """
        user = users["user1"]
        assert not user.is_superuser, "user must be unprivileged"
        assert not user.is_user_of_master_organization, "user must be unprivileged"
        client.force_login(user)
        resp = client.get(
            reverse("flexible-slicer"),
            {"primary_dimension": "organization", "groups": b64json(["metric"])},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0
        assert len(data["results"]) == 0

    def test_user_organization_filtering(self, flexible_slicer_test_data, client, users):
        """
        Test that organizations in reporting API are properly filtered to only contain those
        accessible by current user.
        """
        organization = flexible_slicer_test_data["organizations"][1]
        user = users["user1"]
        UserOrganization.objects.create(user=user, organization=organization)
        assert not user.is_superuser, "user must be unprivileged"
        assert not user.is_user_of_master_organization, "user must be unprivileged"
        client.force_login(user)
        resp = client.get(
            reverse("flexible-slicer"),
            {"primary_dimension": "organization", "groups": b64json(["metric"])},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["pk"] == organization.pk

    @pytest.mark.clickhouse
    @pytest.mark.usefixtures("clickhouse_on_off")
    @pytest.mark.django_db(transaction=True)
    def test_parts_api(self, flexible_slicer_test_data, admin_client):
        """
        Tests that the /parts/ endpoint for getting possible parts after splitting works
        """
        resp = admin_client.get(
            reverse("flexible-slicer-split-parts"),
            {
                "primary_dimension": "organization",
                "groups": b64json(["metric"]),
                "split_by": b64json(["platform"]),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 3
        assert len(data["values"]) == 3
        assert {rec["platform"] for rec in data["values"]} == {
            p.pk for p in flexible_slicer_test_data["platforms"]
        }

    def test_parts_api_with_filter(self, flexible_slicer_test_data, admin_client):
        """
        Tests that the /parts/ endpoint for getting possible parts after splitting works
        """
        pls = flexible_slicer_test_data["platforms"]
        resp = admin_client.get(
            reverse("flexible-slicer-split-parts"),
            {
                "primary_dimension": "organization",
                "groups": b64json(["metric"]),
                "split_by": b64json(["platform"]),
                "filters": b64json({"platform": [p.pk for p in pls[:2]]}),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        assert len(data["values"]) == 2

    def test_get_data_with_parts_no_part(self, flexible_slicer_test_data, admin_client):
        """
        Tests that when getting data and `split_by` is active, we need to provide the `part` arg
        """
        pls = flexible_slicer_test_data["platforms"]
        resp = admin_client.get(
            reverse("flexible-slicer"),
            {
                "primary_dimension": "organization",
                "groups": b64json(["metric"]),
                "split_by": b64json(["platform"]),
                "filters": b64json({"platform": [p.pk for p in pls[:2]]}),
            },
        )
        assert resp.status_code == 400

    def test_get_data_with_parts_part_given(self, flexible_slicer_test_data, admin_client):
        """
        Tests that when getting data and `split_by` is active, we need to provide the `part` arg
        """
        pls = flexible_slicer_test_data["platforms"]
        resp = admin_client.get(
            reverse("flexible-slicer"),
            {
                "primary_dimension": "organization",
                "groups": b64json(["metric"]),
                "split_by": b64json(["platform"]),
                "filters": b64json({"platform": [p.pk for p in pls[:2]]}),
                "part": b64json([pls[0].pk]),
            },
        )
        assert resp.status_code == 200

    @pytest.mark.parametrize("sorted_dim", ["organization", "platform", "metric", "target", "dim1"])
    @pytest.mark.parametrize("desc", [True, False])
    @pytest.mark.parametrize("col_idx", [0, 1, 2])
    def test_order_by(self, flexible_slicer_test_data, admin_client, desc, col_idx, sorted_dim):
        """
        Test that ordering by both explicit and implicit dimensions works
        """
        rt: ReportType = flexible_slicer_test_data["report_types"][0]
        slicer_def = {
            "primary_dimension": "organization" if sorted_dim != "organization" else "platform",
            "groups": b64json([sorted_dim]),
            "filters": b64json({"report_type": rt.pk}),
        }
        resp = admin_client.get(
            reverse("flexible-slicer-possible-values"), {"dimension": sorted_dim, **slicer_def}
        )
        assert resp.status_code == 200
        groups = resp.json()["values"]
        assert len(groups) == 3
        col_name = f"grp-{groups[col_idx][sorted_dim]}"
        sign = "-" if desc else ""
        resp = admin_client.get(
            reverse("flexible-slicer"), {"order_by": f"{sign}{col_name}", **slicer_def}
        )
        assert resp.status_code == 200
        data = resp.json()["results"]
        assert len(data) == 3
        if desc:
            assert data[0][col_name] >= data[1][col_name] >= data[2][col_name]
        else:
            assert data[0][col_name] <= data[1][col_name] <= data[2][col_name]

    # tags
    def test_parts_api_with_tags(self, flexible_slicer_test_data, admin_client, admin_user):
        """
        Tests that the /parts/ endpoint for getting possible parts works properly with tag filter
        """
        tag = TagFactory.create(name="my_platforms", tag_class__scope=TagScope.PLATFORM)
        for platform in flexible_slicer_test_data["platforms"][1:]:
            tag.tag(platform, admin_user)
        resp = admin_client.get(
            reverse("flexible-slicer-split-parts"),
            {
                "primary_dimension": "organization",
                "groups": b64json(["metric"]),
                "split_by": b64json(["platform"]),
                "filters": b64json({"tag__platform": tag.pk}),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        assert len(data["values"]) == 2

    @pytest.mark.parametrize("show_zero", [True, False])
    def test_tag_roll_up(self, flexible_slicer_test_data_with_tags, clients, show_zero):
        """
        Test that tag_roll_up is properly applied to the data. Also checks that only visible
        tags are returned.
        """
        resp = clients["su"].get(
            reverse("flexible-slicer"),
            {
                "primary_dimension": "target",
                "groups": b64json(["metric"]),
                "tag_roll_up": "true",
                "zero_rows": str(show_zero).lower(),
                "order_by": "tag",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == (2 if show_zero else 1)
        tags = flexible_slicer_test_data_with_tags["tags"]
        assert [row["pk"] for row in data["results"]] == (
            [tags[0].pk, tags[2].pk] if show_zero else [tags[0].pk]
        )

    @pytest.mark.parametrize("show_zero", [True, False])
    def test_tag_roll_up_with_hidden_tag_class(
        self, flexible_slicer_test_data_with_tags, clients, users, show_zero
    ):
        """
        Test that tag_roll_up is properly applied to the data. Also checks that tags which the
        user has explicitly hidden are not returned.
        """
        t1, t2, t3 = flexible_slicer_test_data_with_tags["tags"]
        t1.tag_class.change_hidden_for_user(users["su"], True)
        resp = clients["su"].get(
            reverse("flexible-slicer"),
            {
                "primary_dimension": "target",
                "groups": b64json(["metric"]),
                "tag_roll_up": "true",
                "zero_rows": str(show_zero).lower(),
                "order_by": "tag",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == (1 if show_zero else 0)
        assert [row["pk"] for row in data["results"]] == ([t3.pk] if show_zero else [])

    @pytest.mark.parametrize("show_zero", [True, False])
    def test_tag_roll_up_with_hidden_tag_class_explicitly_added(
        self, flexible_slicer_test_data_with_tags, clients, users, show_zero
    ):
        """
        Test that tag_roll_up is properly applied to the data. Also checks that tags which the
        user has explicitly hidden are returned when the tag class is explicitly selected.
        """
        t1, t2, t3 = flexible_slicer_test_data_with_tags["tags"]
        t1.tag_class.change_hidden_for_user(users["su"], True)
        resp = clients["su"].get(
            reverse("flexible-slicer"),
            {
                "primary_dimension": "target",
                "groups": b64json(["metric"]),
                "tag_roll_up": "true",
                "zero_rows": str(show_zero).lower(),
                "tag_class": str(t1.tag_class.pk),  # explicitly add the hidden tag class
                "order_by": "tag",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        # t1 should be present in both cases as t3 will not pass the tag_class filter
        assert data["count"] == 1
        assert [row["pk"] for row in data["results"]] == [t1.pk]

    @pytest.mark.parametrize("order_by", ["tag", "platform"])
    def test_tag_roll_up_with_order_by(
        self, flexible_slicer_test_data_with_tags, clients, order_by
    ):
        """
        Test that when tag_roll_up is requested, only ordering by tag is supported, but other
        versions do not crash.
        This is a test for a bug that was fixed in the code to guard against a regression.
        """
        resp = clients["su"].get(
            reverse("flexible-slicer"),
            {
                "primary_dimension": "platform",
                "groups": b64json(["metric"]),
                "tag_roll_up": "true",
                "zero_rows": False,
                "order_by": order_by,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert (
            data["count"] == 0
        ), "no data should be returned, we are just checking the query does not crash"

    def test_filter_by_tag_class(self, flexible_slicer_test_data_with_tags, clients):
        """
        Test that tag_class filter works in the api.
        """
        tc = flexible_slicer_test_data_with_tags["tag_classes"][0]
        t1, t2, t3 = flexible_slicer_test_data_with_tags["targets"]
        tag1, tag2, tag3 = flexible_slicer_test_data_with_tags["tags"]
        TitleTag.objects.filter(tag=tag1, target=t2).delete()  # untag t2 from tag1

        resp = clients["su"].get(
            reverse("flexible-slicer"),
            {
                "primary_dimension": "target",
                "groups": b64json(["metric"]),
                "filters": b64json({"tag_class__target": [tc.pk]}),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        assert {row["pk"] for row in data["results"]} == {
            t1.pk,
            t3.pk,
        }, "only titles with first tag class should be returned"

    @pytest.mark.parametrize(["sort_desc"], [(True,), (False,)])
    def test_tag_roll_up_order_by_tag(
        self, flexible_slicer_test_data_with_tags, clients, sort_desc
    ):
        """
        Test that it is possible to sort by tag when tag_roll_up is used.
        """
        resp = clients["su"].get(
            reverse("flexible-slicer"),
            {
                "primary_dimension": "target",
                "groups": b64json(["metric"]),
                "tag_roll_up": "true",
                "order_by": ("-" if sort_desc else "") + "tag",
                "zero_rows": "true",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        if sort_desc:
            assert data["results"][0]["pk"] == flexible_slicer_test_data_with_tags["tags"][2].pk
        else:
            assert data["results"][0]["pk"] == flexible_slicer_test_data_with_tags["tags"][0].pk

    def test_parts_api_with_tag_roll_up_tag_class_filter(
        self, flexible_slicer_test_data_with_tags, clients
    ):
        """
        Test that tag_class filter works in the api when tag_roll_up is used.
        """
        resp = clients["su"].get(
            reverse("flexible-slicer"),
            {
                "primary_dimension": "target",
                "groups": b64json(["metric"]),
                "tag_roll_up": "true",
                "zero_rows": "true",
                "tag_class": flexible_slicer_test_data_with_tags["tag_classes"][0].pk,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["results"][0]["pk"] == flexible_slicer_test_data_with_tags["tags"][0].pk

    @pytest.mark.parametrize(
        ["user_type", "expected"],
        [
            ("su", 1301454),  # cannot see tag2
            ("admin1", 235530),  # cannot see tag2, can only see org1
            ("admin2", 0),  # can see all tags, remainder should be zero
        ],
    )
    def test_tag_remainder(self, flexible_slicer_test_data_with_tags, user_type, expected, clients):
        """
        Tests the computation of the remaining usage for stuff without any tag

        Primary dimension: title/target
        Group by: metric
        Tag roll-up: True
        """
        metric_pk = flexible_slicer_test_data_with_tags["metrics"][0].pk
        resp = clients[user_type].get(
            reverse("flexible-slicer-remainder"),
            {
                "primary_dimension": "target",
                "groups": b64json(["metric"]),
                "filters": b64json({"metric": [metric_pk]}),
                "tag_roll_up": "true",
                "zero_rows": "false",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data[f"grp-{metric_pk}"] == expected

    @pytest.mark.parametrize("zero_rows", [True, False])
    def test_trend_mode_year_over_year(self, flexible_slicer_test_data, clients, zero_rows):
        metric_pk = flexible_slicer_test_data["metrics"][0].pk
        resp = clients["su"].get(
            reverse("flexible-slicer"),
            {
                "primary_dimension": "platform",
                "trend_mode": True,
                "base_subset_filters": b64json(
                    {"date": {"start": "2019-01-01", "end": "2019-12-31"}}
                ),
                "compared_subset_filters": b64json(
                    {"date": {"start": "2020-01-01", "end": "2020-12-31"}}
                ),
                "filters": b64json({"metric": [metric_pk]}),
                "zero_rows": zero_rows,
            },
        )
        assert resp.status_code == 200
        data = resp.json()["results"]
        assert len(data) == 3
        assert set(data[0].keys()) == {"pk", "base", "compared", "diff", "reldiff", "_total"}

    @pytest.mark.parametrize("zero_rows", [True, False])
    def test_trend_mode_year_over_year_with_order_by_name(
        self, flexible_slicer_test_data, clients, zero_rows
    ):
        metric_pk = flexible_slicer_test_data["metrics"][0].pk
        resp = clients["su"].get(
            reverse("flexible-slicer"),
            {
                "primary_dimension": "platform",
                "trend_mode": True,
                "base_subset_filters": b64json(
                    {"date": {"start": "2019-01-01", "end": "2019-12-31"}}
                ),
                "compared_subset_filters": b64json(
                    {"date": {"start": "2020-01-01", "end": "2020-12-31"}}
                ),
                "filters": b64json({"metric": [metric_pk]}),
                "zero_rows": zero_rows,
                "order_by": "platform",
            },
        )
        assert resp.status_code == 200
        data = resp.json()["results"]
        assert len(data) == 3
        assert set(data[0].keys()) == {
            "pk",
            "base",
            "compared",
            "diff",
            "reldiff",
            "_total",
            "sort_name",  # extra field coming from the sorting
        }

    @pytest.mark.parametrize(
        ["base_subset_present", "compared_subset_present"],
        [(True, True), (True, False), (False, True), (False, False)],
    )
    @pytest.mark.parametrize("zero_rows", [True, False])
    def test_trend_mode_missing_subfilters(
        self,
        flexible_slicer_test_data,
        clients,
        zero_rows,
        base_subset_present,
        compared_subset_present,
    ):
        subset_config = {}
        if base_subset_present:
            subset_config["base_subset_filters"] = b64json(
                {"date": {"start": "2019-01-01", "end": "2019-12-31"}}
            )
        if compared_subset_present:
            subset_config["compared_subset_filters"] = b64json(
                {"date": {"start": "2020-01-01", "end": "2020-12-31"}}
            )
        resp = clients["su"].get(
            reverse("flexible-slicer"),
            {
                "primary_dimension": "platform",
                "trend_mode": True,
                "zero_rows": zero_rows,
                **subset_config,
            },
        )
        if base_subset_present and compared_subset_present:
            assert resp.status_code == 200
        else:
            assert resp.status_code == 400

    @pytest.mark.parametrize(
        ["rt_idx", "org_idx", "exp_ib_count", "exp_ib_max"],
        ((0, 0, 9, 12), (0, 1, 12, 12), (1, 0, 12, 12), (1, 1, 12, 12), (0, None, 33, 36)),
    )
    def test_report_coverage(
        self, flexible_slicer_test_data, clients, rt_idx, org_idx, exp_ib_count, exp_ib_max
    ):
        """
        Tests that the report coverage endpoint works.
        """
        # make some hole in the data to test that the coverage is computed correctly
        # deletes data for rt1, org1, 2020-01-01 and all platforms
        ImportBatch.objects.filter(
            report_type=flexible_slicer_test_data["report_types"][0],
            organization=flexible_slicer_test_data["organizations"][0],
            date="2020-01-01",
        ).delete()
        fltrs = {}
        if org_idx is not None:
            fltrs["organization"] = [flexible_slicer_test_data["organizations"][org_idx].pk]
        resp = clients["su"].get(
            reverse("flexible-slicer-coverage"),
            {
                "primary_dimension": "platform",
                "groups": b64json(["metric"]),
                "filters": b64json(
                    {
                        "metric": [flexible_slicer_test_data["metrics"][0].pk],
                        "report_type": [flexible_slicer_test_data["report_types"][rt_idx].pk],
                        **fltrs,
                    }
                ),
            },
        )
        assert resp.status_code == 200
        data = resp.json()["overall"]
        assert data["ib_count"] == exp_ib_count
        assert data["ib_max"] == exp_ib_max

    @pytest.mark.parametrize(["end_date", "exp_ib_max"], (("2020-02-28", 2), (None, 0)))
    def test_report_coverage_no_data(
        self,
        clients,
        organizations,
        report_types,
        counter_report_types,
        end_date,
        exp_ib_max,
        interest_rt,
    ):
        pl = PlatformFactory.create()  # create one platform
        org = organizations["branch"]
        report_type = report_types["tr"]
        start_date = "2020-01-01"
        # connect the platform to the organization
        OrganizationPlatform.objects.create(platform=pl, organization=org)
        CredentialsFactory.create(organization=org, platform=pl, report_types=[(5, "TR")])
        resp = clients["su"].get(
            reverse("flexible-slicer-coverage"),
            {
                "primary_dimension": "platform",
                "groups": b64json(["metric"]),
                "filters": b64json(
                    {
                        "report_type": [report_type.pk],
                        "organization": [org.pk],
                        "date": {"start": start_date, "end": end_date},
                    }
                ),
            },
        )
        assert resp.status_code == 200
        data = resp.json()["overall"]
        assert data["ib_count"] == 0
        assert data["ib_max"] == exp_ib_max

    def test_report_coverage_trend_mode(self, flexible_slicer_test_data, clients):
        # make some hole in the data to test that the coverage is computed correctly
        # deletes data for rt1, org1, 2020-01-01 and all platforms
        ImportBatch.objects.filter(
            report_type=flexible_slicer_test_data["report_types"][0],
            organization=flexible_slicer_test_data["organizations"][0],
            date="2020-01-01",
        ).delete()
        resp = clients["su"].get(
            reverse("flexible-slicer-coverage"),
            {
                "primary_dimension": "platform",
                "filters": b64json(
                    {
                        "metric": [flexible_slicer_test_data["metrics"][0].pk],
                        "report_type": [flexible_slicer_test_data["report_types"][0].pk],
                    }
                ),
                "trend_mode": True,
                "base_subset_filters": b64json(
                    {"date": {"start": "2019-01-01", "end": "2019-12-31"}}
                ),
                "compared_subset_filters": b64json(
                    {"date": {"start": "2020-01-01", "end": "2020-12-31"}}
                ),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["base"]["ib_count"] == 9
        assert data["base"]["ib_max"] == 12 * 9
        assert data["compared"]["ib_count"] == 6 + 9 + 9
        assert data["compared"]["ib_max"] == 12 * 9
