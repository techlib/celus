import json
import logging
import traceback
from datetime import timedelta
from typing import Iterable, List, Optional

from core.models import CreatedUpdatedMixin, User
from django.conf import settings
from django.core.mail import send_mail
from django.db import models
from django.db.models import Count, F, Max, Q
from django.db.transaction import atomic
from django.utils.timezone import now
from django_redis import get_redis_connection

logger = logging.getLogger(__name__)


class EventImportance(models.IntegerChoices):
    NORMAL = 10, "Normal"
    HIGH = 20, "Important"

    def default_lifespan(self):
        return 14 if self == EventImportance.NORMAL else 90


class EventCategory(models.TextChoices):
    GENERAL_ANNOUNCEMENTS = "general", "General announcements"
    OVERLAP = "overlap", "Overlap"
    PLATFORM_INFO = "platform", "Platform info"
    SUSHI = "sushi", "SUSHI"
    TAGS = "tags", "Tags"


class HandlingMethod(models.TextChoices):
    IGNORE = "ignore", "Ignore"
    NOTIFY_IN_APP = "notify", "Notify in app"
    EMAIL = "email", "Email"

    @classmethod
    def default(cls):
        return cls.NOTIFY_IN_APP


class EventQuerySet(models.QuerySet):
    def active(self):
        """
        Filters events that are not expired.
        """
        return self.filter(Q(expiration_date__gt=now()) | Q(expiration_date__isnull=True))


class Event(CreatedUpdatedMixin, models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    expiration_date = models.DateTimeField(null=True, blank=True)
    importance = models.PositiveSmallIntegerField(
        choices=EventImportance.choices, default=EventImportance.NORMAL
    )
    category = models.CharField(max_length=10, choices=EventCategory.choices)
    platform = models.ForeignKey(
        "publications.Platform", on_delete=models.CASCADE, null=True, blank=True
    )
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through="UserEvent", related_name="assigned_events"
    )

    objects = EventQuerySet.as_manager()

    def __str__(self):
        return self.title

    def assign_to_users(self, users: Iterable[User], **kwargs) -> List["UserEvent"]:
        """
        Assign this event to a list of users.

        :param users: list of users
        """
        user_to_handling_method = {
            uh.user_id: uh.handling_method
            for uh in UserEventCategoryHandling.objects.filter(
                user__in=users, category=self.category, importance=self.importance
            )
        }
        ues = []
        for user in users:
            handling = user_to_handling_method.get(user.id, HandlingMethod.default())
            if handling != HandlingMethod.IGNORE:
                ues.append(UserEvent(user=user, event=self, handling=handling, **kwargs))
        return UserEvent.objects.bulk_create(ues, ignore_conflicts=True)

    @classmethod
    def create_for_users(
        cls,
        users: Iterable[User],
        send_emails: bool = True,
        send_notifications: bool = True,
        title: str = "",
        description: str = "",
        category: EventCategory = None,
        importance: EventImportance = EventImportance.NORMAL,
        lifespan_days: int = -1,
        **kwargs,
    ) -> "Event":
        """
        Create an event and assign it to a list of users. This is a convenience method to allow
        creating an event and assigning it to users in a single call.
        If not disabled, it would also call the celery task for sending emails to users who have
        email handling method.
        This method explicitly specifies some kwargs for the Event constructor, so that IDEs can
        provide better autocompletion.

        :param users: list of users
        :param send_emails: if True, call the email sending celery task
        :param send_notifications: if True, send notifications to users who have in-app notification
        :param title: event title - passed to the Event constructor
        :param description: event description - passed to the Event constructor
        :param category: event category - passed to the Event constructor
        :param importance: event importance - passed to the Event constructor
        :param lifespan_days: number of days the event is valid for - expiration_date will be set
        relative to the current time - for exact expiration date, use `expiration_date` kwarg.
        If set to `0`, the event will not expire. If set to `-1`, the expiration date will be
        derived from importance - normal events expire in 14 days, important events in 90 days.
        """
        if "expiration_date" not in kwargs and lifespan_days:
            if lifespan_days == -1:
                lifespan_days = importance.default_lifespan()
            kwargs["expiration_date"] = now() + timedelta(days=lifespan_days)
        event = cls.objects.create(
            title=title, description=description, category=category, importance=importance, **kwargs
        )
        event.assign_to_users(users)
        if send_emails:
            event.send_emails()
        if send_notifications:
            event.send_notifications()

        return event

    @classmethod
    def publish_data(cls, data):
        """
        Publishes supplied data to the redis pub-sub channel used for notifications.
        """
        try:
            connection = get_redis_connection("default")
            connection.publish("events", data)
        except Exception as e:
            logger.error("Failed to publish data", exc_info=True)
            raise e

    def send_notifications(self):
        """
        notification is sent for all users who have email or in-app notification handling method
        this is fast because it uses redis pub-sub, so we do it synchronously
        """
        for ue in self.userevent_set.filter(
            handling__in=(HandlingMethod.EMAIL, HandlingMethod.NOTIFY_IN_APP),
            notification_sent_date__isnull=True,
        ):
            ue.send_notification()

    def send_emails(self):
        """
        Send emails for all users who have email handling method and are associated with this event.
        """
        # was any email handling method set for any of the users?
        if self.userevent_set.filter(
            handling=HandlingMethod.EMAIL, email_sent_date__isnull=True
        ).exists():
            # send emails for users who have email handling method
            # we use celery task because we do not want to block the request
            from .tasks import send_unsent_event_emails_task

            send_unsent_event_emails_task.delay()

    @classmethod
    def signal_stats_change(cls, user: User):
        data = json.dumps(
            {"type": "stats", "stats": user.userevent_set.stats(), "user_id": user.pk}
        )
        try:
            cls.publish_data(data)
        except Exception:
            # logging is done in publish_data
            pass


class UserEventQuerySet(models.QuerySet):
    def filter_unmailed(self):
        return self.filter(email_sent_date__isnull=True, handling=HandlingMethod.EMAIL)

    @atomic
    def send_emails(self) -> int:
        sent = 0
        for ue in (
            self.filter_unmailed().select_related("user", "event").select_for_update(nowait=True)
        ):
            if ue.send_email():
                sent += 1
        return sent

    def active(self):
        """
        Filters events that are not expired.
        """
        return self.filter(
            Q(event__expiration_date__gt=now()) | Q(event__expiration_date__isnull=True)
        )

    def stats(
        self,
        read: Optional[bool] = None,
        category: Optional[EventCategory] = None,
        importance: Optional[EventImportance] = None,
        events: Optional[models.QuerySet[Event]] = None,
    ) -> dict:
        qs = self.active()
        event_filter = Q(event__in=events) if events is not None else Q()
        read_agg_filter = (Q(event__category=category) if category is not None else Q()) & (
            Q(event__importance=importance) if importance is not None else Q()
        )
        category_agg_filter = (
            Q(event__importance=importance) if importance is not None else Q()
        ) & (Q(read=read) if read is not None else Q())
        importance_agg_filter = (Q(event__category=category) if category is not None else Q()) & (
            Q(read=read) if read is not None else Q()
        )
        counts = {
            "read": list(
                qs.filter(read_agg_filter & event_filter)
                .values("read")
                .annotate(count=Count("event_id", distinct=True))
            ),
            "importance": list(
                qs.filter(importance_agg_filter & event_filter)
                .values("event__importance")
                .annotate(
                    importance=F("event__importance"),
                    count=Count("event_id", distinct=True),
                )
                .values("count", "importance")
            ),
            "category": list(
                qs.filter(category_agg_filter & event_filter)
                .values("event__category")
                .annotate(
                    category=F("event__category"),
                    count=Count("event_id", distinct=True),
                )
                .values("category", "count")
            ),
        }
        res = dict(
            qs.aggregate(
                total=Count("event_id", distinct=True),
                unread=Count("event_id", filter=Q(read=False), distinct=True),
                newest_pk=Max("event_id"),
            )
        )
        res["counts"] = counts
        return res


class UserEvent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    handling = models.CharField(max_length=10, choices=HandlingMethod.choices)
    read = models.BooleanField(default=False)
    first_read_date = models.DateTimeField(
        null=True, blank=True, help_text="First time the user read the event"
    )
    email_sent_date = models.DateTimeField(
        null=True, blank=True, help_text="Used when publishing the event via email"
    )
    notification_sent_date = models.DateTimeField(
        null=True, blank=True, help_text="Used when publishing the event through the API"
    )
    created = models.DateTimeField(auto_now_add=True)
    error_log = models.TextField(
        blank=True, help_text="Error log if sending email or notification failed"
    )

    objects = UserEventQuerySet.as_manager()

    class Meta:
        unique_together = [("user", "event")]

    def __str__(self):
        return f"{self.user} / {self.event}"

    def send_email(self) -> bool:
        """
        Send the user email if not sent already.
        """
        if self.email_sent_date:
            return False
        if self.handling != HandlingMethod.EMAIL:
            return False
        if not self.user.email:
            return False
        error = False
        try:
            send_mail(
                subject=self.event.title,
                message=self.event.description,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.user.email],
            )
        except Exception as e:
            self.error_log += str(e)
            self.error_log += f"\n\nTraceback:{traceback.format_exc()}"
            error = True
        else:
            self.email_sent_date = now()
        self.save()
        return not error

    def send_notification(self):
        """
        Publish a notification to the user. At present, we use the redis pub-sub functionality
        to get the data to an external websocket server, which then sends the notification to
        the user.
        """
        if self.notification_sent_date:
            return
        if self.handling not in (HandlingMethod.NOTIFY_IN_APP, HandlingMethod.EMAIL):
            # email implies in-app notification as well
            return

        from .serializers import UserEventSerializer

        data = json.dumps(UserEventSerializer(self).data)
        try:
            Event.publish_data(data)
        except Exception as e:
            self.error_log += str(e)
            self.error_log += f"\n\nTraceback:{traceback.format_exc()}"
        else:
            self.notification_sent_date = now()
        self.save()


class UserEventCategoryHandling(models.Model):
    """
    This model is used to store user preferences for handling events of a given category and
    importance.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    category = models.CharField(max_length=10, choices=EventCategory.choices)
    importance = models.PositiveSmallIntegerField(
        choices=EventImportance.choices, default=EventImportance.NORMAL
    )
    handling_method = models.CharField(
        max_length=10, choices=HandlingMethod.choices, default=HandlingMethod.NOTIFY_IN_APP
    )

    class Meta:
        unique_together = [("user", "category", "importance")]

    def __str__(self):
        return f"{self.user} / {self.category} / {self.handling_method}"
