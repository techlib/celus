from core.models import User
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string

from events.models import Event, EventCategory, EventImportance


@receiver(post_save, sender=User)
def user_add_welcome_event_signal(sender, instance, created, **kwargs):
    # we check the settings inside the signal so that it can be changed at runtime
    # - this is useful for tests
    if created and settings.CREATE_USER_WELCOME_EVENTS:
        title = render_to_string("events/welcome_event_title.txt").strip()
        description = render_to_string("events/welcome_event_description.md").strip()
        Event.create_for_users(
            [instance],
            title=title,
            description=description,
            send_emails=False,
            category=EventCategory.GENERAL_ANNOUNCEMENTS,
            importance=EventImportance.NORMAL,
            lifespan_days=90,
        )
