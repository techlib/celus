from rest_framework.permissions import SAFE_METHODS, BasePermission
from tags.models import Tag, TagClass


class TagClassPermissions(BasePermission):

    """
    Checks tag_class object level permissions
    """

    def has_object_permission(self, request, view, obj: Tag):
        if request.method in SAFE_METHODS:
            return obj in TagClass.objects.user_accessible_tag_classes(request.user)

        return obj in TagClass.objects.user_modifiable_tag_classes(request.user)


class TagPermissions(BasePermission):

    """
    Checks tag and tag_class permissions
    """

    def has_object_permission(self, request, view, obj: Tag):
        if request.method in SAFE_METHODS:
            return obj in Tag.objects.user_accessible_tags(request.user)

        return obj.tag_class in TagClass.objects.user_accessible_tag_classes(request.user)
