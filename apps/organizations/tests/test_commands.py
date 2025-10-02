import pytest
from core.fake_data import UserFactory
from core.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from faker import Faker
from publications.fake_data import PlatformFactory
from sushi.fake_data import CounterReportTypeFactory
from sushi.models import SushiCredentials

from organizations.fake_data import OrganizationFactory
from organizations.models import UserOrganization


@pytest.mark.django_db
class TestEnableHarvestReportsCommand:
    @pytest.fixture
    def users_and_orgs(self):
        """Create test users and organizations with various harvest report settings"""
        # Create users with different harvest report settings
        user1 = UserFactory(send_grouped_harvest_reports=False)
        user2 = UserFactory(send_grouped_harvest_reports=True)
        user3 = UserFactory(send_grouped_harvest_reports=False, is_superuser=True)

        # Create organizations
        org1 = OrganizationFactory()
        org2 = OrganizationFactory()

        # Create user-organization relationships with different harvest report settings
        user_org1 = UserOrganization.objects.create(
            user=user1, organization=org1, send_harvest_reports=False, is_admin=True
        )
        user_org2 = UserOrganization.objects.create(
            user=user2, organization=org2, send_harvest_reports=True
        )
        user_org3 = UserOrganization.objects.create(
            user=user3, organization=org1, send_harvest_reports=False
        )

        return {
            "users": [user1, user2, user3],
            "orgs": [org1, org2],
            "user_orgs": [user_org1, user_org2, user_org3],
        }

    def test_dry_run_shows_what_would_be_updated(self, users_and_orgs):
        """Test that dry run shows counts without making changes"""

        with pytest.raises(CommandError, match="use --do-it to really do it"):
            call_command("enable_harvest_reports")

        # Verify no actual changes were made
        assert User.objects.filter(send_grouped_harvest_reports=False).count() == 2
        assert UserOrganization.objects.filter(send_harvest_reports=False).count() == 2

    def test_do_it_flag_enables_all_harvest_reports(self, users_and_orgs):
        """Test that --do-it flag actually enables harvest reports"""

        # Verify initial state
        assert User.objects.filter(send_grouped_harvest_reports=False).count() == 2
        assert UserOrganization.objects.filter(send_harvest_reports=False).count() == 2

        call_command("enable_harvest_reports", "--do-it")

        # Verify all records are now enabled
        assert User.objects.filter(send_grouped_harvest_reports=False).count() == 1, (
            "updated for superuser only"
        )
        assert UserOrganization.objects.filter(send_harvest_reports=False).count() == 1, (
            "updated for is_admins=True"
        )
        assert User.objects.filter(send_grouped_harvest_reports=True).count() == 2
        assert UserOrganization.objects.filter(send_harvest_reports=True).count() == 2

    def test_users_only_flag(self, users_and_orgs):
        """Test --users-only flag updates only User records"""
        call_command("enable_harvest_reports", "--users-only", "--do-it")

        # Verify only users were updated
        assert User.objects.filter(send_grouped_harvest_reports=False).count() == 1, (
            "updated for superuser only"
        )
        assert UserOrganization.objects.filter(send_harvest_reports=False).count() == 2, (
            "nothing updated"
        )

    def test_user_orgs_only_flag(self, users_and_orgs):
        """Test --user-orgs-only flag updates only UserOrganization records"""
        call_command("enable_harvest_reports", "--user-orgs-only", "--do-it")

        # Verify only user-orgs were updated
        assert User.objects.filter(send_grouped_harvest_reports=False).count() == 2, (
            "nothing updated"
        )
        assert UserOrganization.objects.filter(send_harvest_reports=False).count() == 1, (
            "one is_admin updated"
        )

    def test_conflicting_flags_raises_error(self, users_and_orgs):
        """Test that using both --users-only and --user-orgs-only raises error"""
        with pytest.raises(CommandError, match="Cannot use both --users-only and --user-orgs-only"):
            call_command("enable_harvest_reports", "--users-only", "--user-orgs-only")

    def test_deactivate_user_does_not_update_harvest_reports(self, users_and_orgs):
        """Test that deactivating a user does not update harvest reports"""
        user1 = users_and_orgs["users"][0]
        user1.is_active = False
        user1.save()

        user_org1 = users_and_orgs["user_orgs"][0]

        call_command("enable_harvest_reports", "--do-it")

        user1.refresh_from_db()
        assert user1.send_grouped_harvest_reports is False

        user_org1.refresh_from_db()
        assert user_org1.send_harvest_reports is False


@pytest.mark.django_db
class TestLoadSushiCredentialsFromXlsxCommand:
    fake = Faker()
    knowledgebase = {
        "providers": [
            {
                "counter_version": 5,
                "provider": {"url": fake.url()},
                "assigned_report_types": [
                    {"not_valid_after": None, "not_valid_before": None, "report_type": "TR"}
                ],
            },
            {
                "counter_version": 51,
                "provider": {"url": fake.url()},
                "assigned_report_types": [
                    {
                        "not_valid_after": None,
                        "not_valid_before": None,
                        "report_type": "TR",
                        "whitelisted": True,
                    }
                ],
            },
            {
                "counter_version": 51,
                "provider": {"url": fake.url()},
                "assigned_report_types": [
                    {
                        "not_valid_after": None,
                        "not_valid_before": None,
                        "report_type": "IR",
                        "whitelisted": False,
                    }
                ],
            },
        ]
    }

    @pytest.fixture(autouse=True)
    def platforms(self):
        platforms = [
            "AK Journals",
            "AMA Guides",
            "APA PsycNET",
            "APA PsychInfo",
            "APIC Text",
            "ASABE Technical Library",
            "ASM Digital Collection",
            "ASM Journals",
            "ASM Materials Information",
            "ASTM International",
            "Academy of Management",
        ]
        for platform in platforms:
            PlatformFactory(name=platform, knowledgebase=self.knowledgebase)

    @pytest.fixture(autouse=True)
    def counter_reports(self):
        for code in ["TR", "IR"]:
            CounterReportTypeFactory(code=code, counter_version=5)
            CounterReportTypeFactory(
                report_type__short_name=code + "51",
                code=code,
                counter_version=51,
                requires_whitelisting=code == "IR",
            )

    def test_load_sushi_credentials_from_xlsx_single_org_sheet_2(self):
        """
        Test loading of C5 credentials. Look into the file to see what is loaded.
        """
        org = OrganizationFactory()

        assert SushiCredentials.objects.count() == 0
        call_command(
            "load_sushi_credentials_from_xlsx",
            "-f",
            "test-data/import/sushi-credentials.xlsx",
            "--single-org",
            str(org.pk),
            "--parse-sheet-no",
            "2",
            "--do-it",
        )
        assert SushiCredentials.objects.count() == 3, "3 non-empty credentials on sheet 2"
        assert all(s.counter_version == 5 for s in SushiCredentials.objects.all())
        assert {s.title for s in SushiCredentials.objects.all()} == {
            "title 1",
            "title 9",
            "APA PsychI",  # auto-generated title
        }
        assert all(s.counter_reports.count() == 1 for s in SushiCredentials.objects.all())

    def test_load_sushi_credentials_from_xlsx_single_org_sheet_3(self):
        """
        Test loading of C51 credentials. Look into the file to see what is loaded.
        """
        org = OrganizationFactory()

        assert SushiCredentials.objects.count() == 0
        call_command(
            "load_sushi_credentials_from_xlsx",
            "-f",
            "test-data/import/sushi-credentials.xlsx",
            "--single-org",
            str(org.pk),
            "--parse-sheet-no",
            "3",
            "--do-it",
        )
        assert SushiCredentials.objects.count() == 2, "2 non-empty credentials on sheet 3"
        assert all(s.counter_version == 51 for s in SushiCredentials.objects.all())
        assert {s.title for s in SushiCredentials.objects.all()} == {
            "title 1 - 5.1",
            "AMA Guides (C51)",  # auto-generated title
        }
        # test that only the whitelisted report is loaded
        for s in SushiCredentials.objects.all():
            assert list(s.counter_reports.values_list("code", flat=True)) == ["TR"], (
                "just TR is loaded"
            )

    @pytest.mark.parametrize("harvest_months", [12, 6, 0, None])
    def test_load_sushi_credentials_from_xlsx_autoharvest(self, harvest_months):
        """
        Test loading of C5 credentials with auto-harvesting
        """
        org = OrganizationFactory()

        assert SushiCredentials.objects.count() == 0
        extra = ["--harvest-months", str(harvest_months)] if harvest_months else []
        call_command(
            "load_sushi_credentials_from_xlsx",
            "-f",
            "test-data/import/sushi-credentials.xlsx",
            "--single-org",
            str(org.pk),
            "--parse-sheet-no",
            "2",
            "--do-it",
            *extra,
        )
        assert SushiCredentials.objects.count() == 3, "3 non-empty credentials on sheet 2"
        assert all(s.counter_version == 5 for s in SushiCredentials.objects.all())
        for cr in SushiCredentials.objects.all():
            assert cr.fetchintention_set.count() == (harvest_months or 0)
