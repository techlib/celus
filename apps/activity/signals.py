from activity.models import UserActivity
from django.contrib.auth import user_logged_in
from django.dispatch import receiver


@receiver(user_logged_in)
def log_user_activity_login(request, user, **kwargs):
    UserActivity.objects.create(user=user, action_type=UserActivity.ACTION_TYPE_LOGIN)
