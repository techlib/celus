import pytest
from core.fake_data import UserFactory
from core.models import User
from django.core.management import call_command
from django.core.management.base import CommandError

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
