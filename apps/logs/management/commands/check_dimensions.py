from collections import Counter, namedtuple

from django.core.management.base import BaseCommand, CommandError
from django.db.transaction import atomic

from logs.models import Dimension, DimensionText

Dim = namedtuple("Dim", ["short_name", "name", "texts"])


REQUIRED_DIMS = [Dim("YOP", "Year of publication", [f"{i:04}" for i in range(1, 2101)] + ["9999"])]


class Command(BaseCommand):
    help = """\
Checks that mandatory Dimension are present with linked DimensionTexts

Dimensions which are required:
* YOP
"""

    def add_arguments(self, parser):
        parser.add_argument("--do-it", dest="doit", action="store_true")

    @atomic
    def handle(self, *args, **options):
        stats = Counter()
        for dim in REQUIRED_DIMS:
            dimension, created = Dimension.objects.get_or_create(
                short_name=dim.short_name, defaults={"name": dim.name}
            )
            if created:
                stats["created_dims"] += 1
            else:
                stats["existing_dims"] += 1

            existing_texts = set(
                DimensionText.objects.filter(dimension=dimension).values_list("text", flat=True)
            )
            missing_texts = set(dim.texts) - existing_texts
            stats["existing_texts"] += len(existing_texts)

            to_add = [DimensionText(dimension=dimension, text=text) for text in missing_texts]
            DimensionText.objects.bulk_create(to_add)
            stats["created_texts"] += len(to_add)

        print(stats)

        if not options["doit"] and (stats["created_dims"] or stats["created_texts"]):
            raise CommandError("Preventing DB commit, use --do-it to really do it ;)")
