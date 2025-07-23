from core.models import DataSource
from core.permissions import SuperuserOrAdminPermission
from publications import models as publications_models
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, UpdateModelMixin
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND
from rest_framework.viewsets import GenericViewSet
from sushi import models as sushi_models

from .models import Platform
from .serializers import (
    ApplySerializer,
    CelusPlatformSerializer,
    LinkSerializer,
    PlatformDiffSerializer,
    UpdateNotesSerializer,
)


class PlatformDiffViewSet(ListModelMixin, UpdateModelMixin, GenericViewSet):
    serializer_class = PlatformDiffSerializer
    permission_classes = [SuperuserOrAdminPermission]
    queryset = Platform.objects.all()

    def get_serializer_class(self):
        if self.action in ["update", "partial_update"]:
            return UpdateNotesSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        return super().get_queryset().order_by("name", "abbrev")

    @action(
        methods=["GET"],
        detail=False,
        url_path="unlinked-platforms",
        serializer_class=CelusPlatformSerializer,
    )
    def unlinked_platforms(self, request):
        qs = (
            publications_models.Platform.objects.filter(counter_registry_id__isnull=True)
            .exclude(source__type=DataSource.TYPE_ORGANIZATION)
            .order_by("name", "short_name")
        )
        serializer = CelusPlatformSerializer(qs, many=True)
        return Response(serializer.data)

    @action(methods=["POST"], detail=False, url_path="apply", serializer_class=ApplySerializer)
    def apply(self, request):
        serializer = ApplySerializer(data=request.data)

        if not serializer.is_valid():
            return Response(data=serializer.errors, status=HTTP_400_BAD_REQUEST)
        platforms = Platform.objects.filter(
            id__in=[e["id"] for e in serializer.validated_data["updates"]]
        )
        updates_map = {e["id"]: e for e in serializer.validated_data["updates"]}

        to_update = []
        to_create = []
        for platform in platforms:
            created, obj = platform.apply_related_platform(
                **{k: v for k, v in updates_map[platform.id].items() if k != "id"}
            )
            if created:
                to_create.append(obj)
            else:
                to_update.append(obj)

        if to_create:
            created_objs = publications_models.Platform.objects.bulk_create(to_create)
        else:
            created_objs = []
        if to_update:
            publications_models.Platform.objects.bulk_update(
                to_update, fields=["name_en", "short_name", "provider_en", "url", "knowledgebase"]
            )

        affected_ids = [e.pk for e in created_objs] + [e.pk for e in to_update]

        # Update affected report types
        publications_models.Platform.objects.filter(
            pk__in=affected_ids
        ).update_counter_reports_from_knowledgebase()
        # Update report types of affected credentials
        sushi_models.SushiCredentials.objects.filter(
            platform_id__in=affected_ids
        ).update_report_types_based_on_platform()
        # Update urls of affected credentials
        for platform in created_objs + to_update:
            platform.update_related_credentials_url()

        return Response({"created": len(to_create), "updated": len(to_update)})

    @action(methods=["POST"], detail=True, url_path="link", serializer_class=LinkSerializer)
    def link(self, request, pk):
        platform_diff = self.get_object()
        serializer = LinkSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(data=serializer.errors, status=HTTP_400_BAD_REQUEST)
        if publications_models.Platform.objects.filter(
            counter_registry_id=platform_diff.id
        ).exists():
            # registry id already used
            return Response(data=serializer.errors, status=HTTP_404_NOT_FOUND)

        celus_platform = publications_models.Platform.objects.get(pk=serializer.data["platform_id"])
        celus_platform.counter_registry_id = platform_diff.id
        celus_platform.save()
        return Response()
