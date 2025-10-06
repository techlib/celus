import logging
from argparse import FileType
from collections import Counter
from io import BufferedReader

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.db.transaction import atomic
from nibbler.logic.dict_reader import get_dict_reader_from_csv
from organizations.models import Organization, UserOrganization

from core.logic.type_conversion import strtobool
from core.models import User

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Create/sync users with a CSV table. Columns can be: "
        '"first_name","last_name" (or "name"),"email","staff","organization","org_admin"; '
        'optionally: "superuser", "staff"'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "-f",
            dest="csv_file",
            help="CSV file to import - columns: email, first_name, last_name, organization, "
            "org_admin; optionally: superuser, staff",
            type=FileType("rb"),
        )
        parser.add_argument("--debug", dest="debug", action="store_true", help="Extra logging")
        parser.add_argument("--do-it", dest="doit", action="store_true")

    @classmethod
    def cleanup(cls, value: str):
        # strip any whitespace, comas, etc.
        return value.strip().strip(",").strip()

    @atomic
    def handle(self, *args, **options):
        stats = Counter()
        if not options["debug"]:
            logger.setLevel(logging.WARNING)
        else:
            logger.setLevel(logging.DEBUG)

        reader = get_dict_reader_from_csv(BufferedReader(options["csv_file"]))
        for i, row in enumerate(reader, start=2):
            email = row.get("email")
            if not email:
                raise ValueError('Column "email" is required')
            email = email.strip()
            username = row.get("username", email)
            superuser = bool(strtobool(row.get("superuser", "False")))
            staff = strtobool(row.get("staff", "False"))
            name = row.get("name", "")
            first_name = row.get("first_name") or (name.split()[0] if name else "")
            last_name = row.get("last_name") or (name.split()[-1] if name else "")
            user_params = {
                "username": self.cleanup(username),
                "is_superuser": superuser,
                "is_staff": staff,
                "first_name": self.cleanup(first_name),
                "last_name": self.cleanup(last_name),
            }
            user, created = User.objects.update_or_create(email=email, defaults=user_params)
            if created:
                stats["user_created"] += 1
                logger.info("%03d: created user %s: %s", i, email, user_params)
            else:
                stats["user_existed"] += 1
                logger.info("%03d: updating user %s: %s", i, email, user_params)
            org_name = row.get("org_id") or row.get("organization")
            org_name = self.cleanup(org_name)
            if org_name:
                if org_name.isdigit():
                    filters = Q(ext_id=org_name) | Q(internal_id=org_name)
                else:
                    filters = Q(short_name=org_name) | Q(name=org_name)
                organization = Organization.objects.get(filters)
                is_admin = strtobool(row.get("org_admin", "False"))
                uo, created = UserOrganization.objects.update_or_create(
                    user=user, organization=organization, defaults={"is_admin": is_admin}
                )
                if created:
                    stats["user-org_created"] += 1
                else:
                    stats["user-org_existed"] += 1
            else:
                logger.warning("No organization specified for user: %s", email)

        logger.warning(f"Import stats: {stats}")
        if not options["doit"]:
            raise ValueError("preventing db commit, use --do-it to really do it ;)")
