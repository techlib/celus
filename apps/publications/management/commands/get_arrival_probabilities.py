from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from publications.logic import arrival_probabilities
from publications.models import Platform


class Command(BaseCommand):
    help = "Get quantiles of data arrival probabilities and n (from how many\
        samples were they obtained)"

    def add_arguments(self, parser):
        parser.add_argument("-p", dest="platform_id", type=int, help="Platform ID")
        parser.add_argument("-a", dest="all_platforms", action="store_true", help="All platforms")

    @atomic
    def handle(self, *args, **options):
        if options["platform_id"]:
            print(arrival_probabilities.get_probabilities(platform_id=options.get("platform_id")))
        elif options["all_platforms"]:
            for p in Platform.objects.all():
                count, probs = arrival_probabilities.get_probabilities(platform_id=p.id)
                if count:
                    print(p.pk, p.name, count, probs[2], probs[4])
        else:
            print(arrival_probabilities.get_probabilities(platform_id=None))
