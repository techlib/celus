import logging

import celery
from core.context_managers import logged_task
from core.logic.error_reporting import email_if_fails

from events.models import UserEvent

logger = logging.getLogger(__name__)


@celery.shared_task
@logged_task
@email_if_fails
def send_unsent_event_emails_task():
    """
    Send emails for all unsent events.
    """
    logger.debug("Sent %d emails", UserEvent.objects.send_emails())
