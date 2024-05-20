import json

from django.core.management.base import BaseCommand

from core.logic.lookup_json_by_title import lookup_json_by_title


class Command(BaseCommand):
    help = (
        "Search through all files related to a specific title and print corresponding parts of "
        "the json to stdout"
    )

    def add_arguments(self, parser):
        parser.add_argument("title_id", help="Title id from publications/title (Title/Database)")
        parser.add_argument(
            "--json", help="Print only valid json", action="store_true", dest="json"
        )
        parser.add_argument(
            "--indent",
            help="Number of spaces to indent output with (0 is no indent)",
            dest="indent",
            type=int,
            default=2,
        )

    def handle(self, *args, **options):
        indent = options["indent"]
        indent = indent if indent > 0 else None

        lookup, err = lookup_json_by_title(options["title_id"])

        if options["json"]:
            self.stdout.write(json.dumps(lookup, indent=indent, ensure_ascii=False))
        else:
            for file, items in lookup.items():
                self.stdout.write()
                self.stdout.write(self.style.WARNING(file))
                for d in items:
                    self.stdout.write(json.dumps(d, indent=indent, ensure_ascii=False)[2:-1])
                self.stdout.write()

        for file, e in err:
            self.stderr.write(self.style.WARNING(file))
            self.stderr.write(self.style.ERROR("  Exception reading file: " + str(e)))
