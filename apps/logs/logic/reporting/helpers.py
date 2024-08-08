from typing import Optional

from core.models import User
from django.db.models import Q
from tags.models import Tag, TagClass


def user_visible_tags(user: User, selected_tag_class: Optional[int] = None) -> Q:
    """
    This is a helper function used in reporting to get the tags that are visible to the user.
    It takes into account what the user has access to, but also what the user has hidden explicitly.

    :param user: user for which to get the tags
    :param selected_tag_class: if provided, this class was explicitly selected by the user
           - we want to include it, even if it is marked hidden, and exclude any other
    """
    tag_class_ids = (
        TagClass.objects.with_user_visible_tags(user)
        .annotate_hidden(user)
        .filter(Q(hidden=False) | Q(pk=selected_tag_class))
        .values_list("pk", flat=True)
    )
    return Q(pk__in=Tag.objects.user_accessible_tags(user).filter(tag_class_id__in=tag_class_ids))
