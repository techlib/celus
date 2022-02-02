import csv
from io import StringIO

from api.models import OrganizationAPIKey
from django.core.management.base import BaseCommand, CommandError
from django.db.transaction import atomic
from organizations.models import Organization


class Command(BaseCommand):

    help = "Create an API key for each organization"

    def add_arguments(self, parser):
        parser.add_argument(
            "org_ids",
            nargs="*",
            type=int,
            help=(
                "Organization PKs. "
                "If none, present keys will be created for organizations, "
                "which don’t have any API key yet."
            ),
        )
        parser.add_argument("--do-it", dest="doit", action="store_true")

    @atomic
    def handle(self, *args, **options):
        api_keys = self.create_keys(org_ids=options["org_ids"])
        out = StringIO()
        writer = csv.writer(out)
        writer.writerow(['organization id', 'organization ext_id', 'organization name', 'api_key'])
        for api_key, key_value in api_keys:
            writer.writerow(
                [
                    api_key.organization.pk,
                    api_key.organization.ext_id,
                    api_key.organization.name,
                    key_value,
                ]
            )

        print(out.getvalue())
        if not options["doit"]:
            raise CommandError("Preventing DB commit, use --do-it to really do it ;)")

    @staticmethod
    def create_keys(org_ids=None):
        query = {"pk__in": org_ids} if org_ids else {"api_keys__isnull": True}

        return [
            OrganizationAPIKey.objects.create_key(
                organization=organization, name=organization.name[:50]
            )
            for organization in Organization.objects.filter(**query)
        ]
