from core.models import User
from django.db.models import Prefetch
from impersonate.views import impersonate, stop_impersonate
from organizations.models import UserOrganization
from rest_framework import mixins, status
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from .permissions import ImpersonatedSuperuserOrAdminPermission, users_impersonable
from .serializers import ImpersonateListSerializer, ImpersonateSetSerializer


class ImpersonateViewSet(
    mixins.ListModelMixin, mixins.UpdateModelMixin, GenericViewSet,
):
    queryset = User.objects.filter(is_superuser=False)
    permission_classes = (ImpersonatedSuperuserOrAdminPermission,)

    def get_serializer_class(self):
        if self.action == "list":
            return ImpersonateListSerializer
        elif self.action == "update":
            return ImpersonateSetSerializer

    def get_queryset(self):
        return users_impersonable(self.request).prefetch_related(
            Prefetch(
                'userorganization_set',
                queryset=UserOrganization.objects.select_related('organization'),
            )
        )

    def perform_update(self, serializer):

        user = self.get_object()
        if self.request.user.pk != user.pk:
            # Deactivate impersonation if active
            stop_impersonate(self.request)

            # Set original user for the current request
            self.request.user = self.request.real_user

            # this function may raise an exception when user is not found,
            # but that can't happen here
            impersonate(self.request, user.pk)

        return Response(status=status.HTTP_200_OK)
