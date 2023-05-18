from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from publications.logic.arrival_probabilities import update_all_arrival_curves


class Command(BaseCommand):
    help = "Update arrival probabilities for all platforms"

    @atomic
    def handle(self, *args, **options):
        update_all_arrival_curves()
