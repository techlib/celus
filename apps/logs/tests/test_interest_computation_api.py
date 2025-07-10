import pytest
from django.core.management import call_command
from django.urls import reverse
from organizations.fake_data import OrganizationFactory
from publications.fake_data import PlatformFactory
from publications.tests.conftest import interest_groups, interest_rt  # noqa - fixture
from rest_framework import status
from rest_framework.test import APIClient

from logs.models import (
    Dimension,
    DimensionFilter,
    DimensionText,
    InterestDimensionValueMapping,
    InterestGroup,
    Metric,
    ReportInterestMetric,
    ReportType,
    ReportTypeToDimension,
)


@pytest.mark.django_db
class TestInterestComputationDescriptionAPI:
    @pytest.fixture(autouse=True)
    def setup_method(self):
        self.client = APIClient()
        self.organization = OrganizationFactory()
        self.platform = PlatformFactory()

        # Create test user and authenticate
        from core.models import User

        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass"
        )
        self.user.organizations.add(self.organization)
        self.client.force_authenticate(user=self.user)

        # Clean up any existing global configs and profiles
        from logs.models import InterestConfig, InterestProfile

        InterestConfig.objects.filter(organization=None).delete()
        # Optionally, clean up orphaned profiles (not strictly necessary)
        for profile in InterestProfile.objects.all():
            if not profile.interest_config.filter(organization=None).exists():
                profile.delete()

        # Create interest report type
        self.interest_rt = ReportType.objects.create(short_name="interest", name="Interest")

        # Create dimensions
        self.access_type_dim = Dimension.objects.create(
            short_name="Access_Type", name="Access Type"
        )
        self.original_rt_dim = Dimension.objects.create(
            short_name="Original_Report_Type", name="Original Report Type"
        )

        # Create dimension texts
        self.controlled_text = DimensionText.objects.create(
            dimension=self.access_type_dim, text="Controlled"
        )
        self.free_text = DimensionText.objects.create(dimension=self.access_type_dim, text="Free")

        # Create report type to dimension relationships
        self.interest_rtdim = ReportTypeToDimension.objects.create(
            report_type=self.interest_rt, dimension=self.access_type_dim, position=0
        )
        self.original_rtdim = ReportTypeToDimension.objects.create(
            report_type=self.interest_rt, dimension=self.original_rt_dim, position=1
        )

        # Create interest profile
        self.interest_profile = InterestProfile.objects.create(
            short_name="total", name="Total", desc="Interest profile using Total metrics"
        )

        # Create global interest config (organization=None)
        self.global_interest_config = InterestConfig.objects.create(
            organization=None, interest_profile=self.interest_profile
        )

        # Create interest config
        self.interest_config = InterestConfig.objects.create(
            organization=self.organization, interest_profile=self.interest_profile
        )

        # Create metric first
        self.metric = Metric.objects.create(
            short_name="Total_Item_Requests", name="Total Item Requests"
        )

        # Create interest group
        self.interest_group = InterestGroup.objects.create(
            short_name="full_text",
            name="Full Text",
            metric=self.metric,
            position=1,
            important=True,
            implies_availability=True,
        )

        # Create report types with hierarchy
        self.report_type_a = ReportType.objects.create(short_name="TR_A", name="Title Report A")
        self.report_type_b = ReportType.objects.create(short_name="TR_B", name="Title Report B")
        self.report_type_a.superseded_by = self.report_type_b
        self.report_type_a.save()

        # Create report interest metrics for both report types
        self.rim_a = ReportInterestMetric.objects.create(
            report_type=self.report_type_a,
            metric=self.metric,
            interest_group=self.interest_group,
            interest_profile=None,
        )
        self.rim_b = ReportInterestMetric.objects.create(
            report_type=self.report_type_b,
            metric=self.metric,
            interest_group=self.interest_group,
            interest_profile=None,
        )

        # Create dimension filter
        self.dimension_filter = DimensionFilter.objects.create(
            dimension=self.access_type_dim, values=["Controlled"], negated=False
        )
        self.rim_a.filters.add(self.dimension_filter)
        self.rim_b.filters.add(self.dimension_filter)

        # Create source report type to dimension relationship
        self.source_rtdim = ReportTypeToDimension.objects.create(
            report_type=self.report_type_a, dimension=self.access_type_dim, position=0
        )

        # Create dimension mapping
        self.dimension_mapping = InterestDimensionValueMapping.objects.create(
            interest_rtdim=self.interest_rtdim,
            source_rtdim=self.source_rtdim,  # now we have a source mapping
            default_value="Controlled",
            mapping={"Free": ["Free_To_Read", "Open"]},
        )

    def test_get_global_interest_computation_description(self):
        """Test getting global interest computation description"""
        url = reverse("interest-computation-description")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        # Check basic structure
        assert "organization" in data
        assert "interest_config" in data
        assert "report_type_hierarchy" in data
        assert "interest_definitions" in data
        assert "dimension_mappings" in data

        # Check organization is None for global
        assert data["organization"] is None

        # Check interest config
        assert data["interest_config"]["interest_profile"]["short_name"] == "total"

    def test_get_organization_interest_computation_description(self):
        """Test getting organization-specific interest computation description"""
        url = reverse("interest-computation-description")
        response = self.client.get(url, {"organization_id": self.organization.pk})

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        # Check organization is set
        assert data["organization"]["pk"] == self.organization.pk
        assert data["organization"]["name"] == self.organization.name

        # Check interest config
        assert data["interest_config"]["organization"] == self.organization.pk
        assert data["interest_config"]["interest_profile"]["short_name"] == "total"

    def test_get_interest_computation_description_unauthorized_organization(self):
        """Test getting interest computation description for unauthorized organization"""
        other_org = OrganizationFactory()
        url = reverse("interest-computation-description")
        response = self.client.get(url, {"organization_id": other_org.pk})

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_interest_computation_description_nonexistent_organization(self):
        """
        Test getting interest computation description for nonexistent organization.
        Should return 403 the same way as for unauthorized organization in order not
        to leak information about the existence of the organization.
        """
        url = reverse("interest-computation-description")
        response = self.client.get(url, {"organization_id": 99999})

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_interest_computation_description_unauthenticated(self):
        """Test getting interest computation description without authentication"""
        self.client.force_authenticate(user=None)
        url = reverse("interest-computation-description")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_interest_definitions_structure(self):
        """Test that interest definitions have the correct structure"""
        url = reverse("interest-computation-description")
        response = self.client.get(url, {"organization_id": self.organization.pk})

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        # Check interest definitions
        assert len(data["interest_definitions"]) >= 2

        rim_data_a = data["interest_definitions"][0]
        rim_data_b = data["interest_definitions"][1]
        assert "pk" in rim_data_a
        assert "metric" in rim_data_a
        assert "interest_group" in rim_data_a
        assert "filters" in rim_data_a

        assert "pk" in rim_data_b
        assert "metric" in rim_data_b
        assert "interest_group" in rim_data_b
        assert "filters" in rim_data_b

        # Check metric structure
        assert rim_data_a["metric"]["short_name"] == "Total_Item_Requests"
        assert rim_data_a["metric"]["name"] == "Total Item Requests"
        assert rim_data_b["metric"]["short_name"] == "Total_Item_Requests"
        assert rim_data_b["metric"]["name"] == "Total Item Requests"

        # Check interest group structure
        assert rim_data_a["interest_group"]["short_name"] == "full_text"
        assert rim_data_a["interest_group"]["name"] == "Full Text"
        assert rim_data_a["interest_group"]["important"] is True
        assert rim_data_a["interest_group"]["implies_availability"] is True

        assert rim_data_b["interest_group"]["short_name"] == "full_text"
        assert rim_data_b["interest_group"]["name"] == "Full Text"
        assert rim_data_b["interest_group"]["important"] is True
        assert rim_data_b["interest_group"]["implies_availability"] is True

        # Check filters structure
        assert len(rim_data_a["filters"]) >= 1
        filter_data_a = rim_data_a["filters"][0]
        assert filter_data_a["dimension"]["short_name"] == "Access_Type"
        assert filter_data_a["values"] == ["Controlled"]
        assert filter_data_a["negated"] is False

        assert len(rim_data_b["filters"]) >= 1
        filter_data_b = rim_data_b["filters"][0]
        assert filter_data_b["dimension"]["short_name"] == "Access_Type"
        assert filter_data_b["values"] == ["Controlled"]
        assert filter_data_b["negated"] is False

    def test_dimension_mappings_structure(self):
        """Test that dimension mappings have the correct structure"""
        url = reverse("interest-computation-description")
        response = self.client.get(url, {"organization_id": self.organization.pk})

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        # Check dimension mappings
        assert len(data["dimension_mappings"]) >= 1

        mapping_data = data["dimension_mappings"][0]
        assert "pk" in mapping_data
        assert "interest_dimension" in mapping_data
        assert "source_dimension" in mapping_data
        assert "default_value" in mapping_data
        assert "mapping" in mapping_data

        # Check specific mapping
        assert mapping_data["interest_dimension"] == "Access_Type"
        assert mapping_data["default_value"] == "Controlled"
        assert mapping_data["mapping"] == {"Free": ["Free_To_Read", "Open"]}

    def test_report_type_hierarchy_structure(self):
        """Test that report type hierarchy has the correct structure"""
        url = reverse("interest-computation-description")
        response = self.client.get(url, {"organization_id": self.organization.pk})

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        # Check report type hierarchy
        assert len(data["report_type_hierarchy"]) >= 2

        # Sort by short_name for deterministic order
        sorted_rts = sorted(data["report_type_hierarchy"], key=lambda rt: rt["short_name"])
        rt_data_a = sorted_rts[0]
        rt_data_b = sorted_rts[1]
        assert "pk" in rt_data_a
        assert "short_name" in rt_data_a
        assert "name" in rt_data_a
        assert "superseded_by" in rt_data_a

        assert "pk" in rt_data_b
        assert "short_name" in rt_data_b
        assert "name" in rt_data_b
        assert "superseded_by" in rt_data_b

        # Check specific report type
        assert rt_data_a["short_name"] == "TR_A"
        assert rt_data_a["name"] == "Title Report A"
        assert rt_data_a["superseded_by"] == ReportType.objects.get(short_name="TR_B").pk
        assert rt_data_b["short_name"] == "TR_B"
        assert rt_data_b["name"] == "Title Report B"
        assert rt_data_b["superseded_by"] is None


@pytest.mark.django_db()
class TestRealWorldInterestComputationAPI:
    def test_create_interest_definitions(self, admin_client, interest_groups, interest_rt):
        call_command("check_report_type_dimensions", "--fix-it")
        call_command("check_interest_definitions", "--fix-it")

        url = reverse("interest-computation-description")
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert data["report_type_hierarchy"]
        tr = next(rt for rt in data["report_type_hierarchy"] if rt["short_name"] == "TR")
        assert tr["superseded_by"] == ReportType.objects.get(short_name="TR51").pk


@pytest.mark.django_db()
class TestInterestGroupDefinitionsAPI:
    def test_get_interest_group_definitions(self, admin_client, interest_groups, interest_rt):
        call_command("check_report_type_dimensions", "--fix-it")
        call_command("check_interest_definitions", "--fix-it")

        ig_full_text = interest_groups["full_text"]
        url = reverse("interest-group-definitions", kwargs={"pk": ig_full_text.pk})
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        assert data["report_types"]
        assert {rt["short_name"] for rt in data["report_types"]} == {
            "TR",
            "TR51",
            "IR51",
            "JR1",
            "JR1a",
            "BR2",
        }
        tr = next(rt for rt in data["report_types"] if rt["short_name"] == "TR")
        assert tr["superseded_by"] == ReportType.objects.get(short_name="TR51").pk
