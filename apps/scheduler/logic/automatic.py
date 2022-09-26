from core.logic.dates import last_month
from django.conf import settings
from django.db import transaction
from sushi.models import AttemptStatus, CounterReportsToCredentials, SushiFetchAttempt

from ..models import Automatic, FetchIntention


def update_cr2c(automatic: Automatic, cr2c: CounterReportsToCredentials):
    if (
        cr2c.credentials.enabled
        and cr2c.broken is None
        and cr2c.credentials.broken is None
        and cr2c.credentials.is_verified
    ):
        # We need to make sure that the intentions exists
        attrs = {
            "harvest": automatic.harvest,
            "start_date": automatic.month,
            "end_date": automatic.month_end,
            "credentials": cr2c.credentials,
            "counter_report": cr2c.counter_report,
        }

        # There is already an intention which is going to be performed
        if FetchIntention.objects.filter(**attrs, when_processed__isnull=True).exists():
            return

        # There might be an unfinished retry chain
        # we need to obtain the last intention
        if last_fi := FetchIntention.objects.filter(**attrs).order_by('pk').last():
            # Try to run handler to recreate a retry
            if handler := last_fi.get_handler():
                handler()

        else:
            # No intention found -> create a new one
            FetchIntention.objects.create(
                not_before=Automatic.trigger_time(automatic.month), **attrs
            )

    else:
        # delete otherwise
        FetchIntention.objects.select_for_update(skip_locked=True).filter(
            harvest=automatic.harvest,
            start_date=automatic.month,
            end_date=automatic.month_end,
            credentials=cr2c.credentials,
            counter_report=cr2c.counter_report,
            when_processed__isnull=True,
        ).delete()


@transaction.atomic
def update_verified_for_automatic_scheduling(attempt: SushiFetchAttempt):

    if not settings.AUTOMATIC_HARVESTING_ENABLED:
        # skip when automatic scheduling disabled
        return

    # Only when the attempt is successful
    if attempt.status not in [AttemptStatus.IMPORTING, AttemptStatus.NO_DATA]:
        return

    # Only update for current credentials
    if not attempt.credentials.is_verified:
        return

    automatic = Automatic.get_or_create(
        month=last_month(), organization=attempt.credentials.organization
    )

    # When credentials become verified rescheduler for all report types
    for cr2c in CounterReportsToCredentials.objects.filter(credentials=attempt.credentials):
        update_cr2c(automatic, cr2c)
