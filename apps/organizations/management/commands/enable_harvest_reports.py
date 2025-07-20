from core.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db.transaction import atomic

from organizations.models import UserOrganization


class Command(BaseCommand):
    help = """
    Enables sending of harvest reports for all users by setting:
    - User.send_grouped_harvest_reports to True for consortial admins
    - UserOrganization.send_harvest_reports to True for all direct admin members

    This command will update all users and user-organization relationships to enable
    harvest report emails. Use --do-it flag to actually perform the changes.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--do-it",
            dest="doit",
            action="store_true",
            help="Actually perform the changes (without this flag, only a dry-run is performed)",
        )
        parser.add_argument(
            "--users-only",
            dest="users_only",
            action="store_true",
            help="Only update User.send_grouped_harvest_reports, skip UserOrganization records",
        )
        parser.add_argument(
            "--user-orgs-only",
            dest="user_orgs_only",
            action="store_true",
            help="Only update UserOrganization.send_harvest_reports, skip User records",
        )

    @atomic
    def handle(self, *args, **options):
        if options["users_only"] and options["user_orgs_only"]:
            raise CommandError("Cannot use both --users-only and --user-orgs-only flags together")

        self.stdout.write(self.style.HTTP_INFO("Starting harvest reports enablement process..."))

        users_updated = 0
        user_orgs_updated = 0

        # Update User records unless --user-orgs-only is specified
        if not options["user_orgs_only"]:
            users_to_update = User.objects.filter(
                send_grouped_harvest_reports=False
            ).filter_consortium_admins()
            users_count = users_to_update.count()

            if options["doit"]:
                users_updated = users_to_update.update(send_grouped_harvest_reports=True)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Updated {users_updated} User records to enable grouped harvest reports"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"DRY RUN: Would update {users_count} User records "
                        "to enable grouped harvest reports"
                    )
                )

        # Update UserOrganization records unless --users-only is specified
        if not options["users_only"]:
            user_orgs_to_update = UserOrganization.objects.filter(
                send_harvest_reports=False, is_admin=True
            )
            user_orgs_count = user_orgs_to_update.count()

            if options["doit"]:
                user_orgs_updated = user_orgs_to_update.update(send_harvest_reports=True)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Updated {user_orgs_updated} UserOrganization records "
                        "to enable harvest reports"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"DRY RUN: Would update {user_orgs_count} UserOrganization records "
                        "to enable harvest reports"
                    )
                )

        if not options["doit"]:
            self.stdout.write(
                self.style.ERROR(
                    "This was a dry run. Use --do-it flag to actually perform the changes."
                )
            )
            raise CommandError("Preventing DB commit, use --do-it to really do it ;)")
        else:
            total_updated = users_updated + user_orgs_updated
            self.stdout.write(
                self.style.SUCCESS(
                    f"🎉 Successfully completed! Updated {users_updated} users and "
                    f"{user_orgs_updated} user-organization relationships "
                    f"({total_updated} total records)."
                )
            )
