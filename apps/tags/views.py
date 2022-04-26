from typing import Optional

from allauth.utils import build_absolute_uri
from django.db import DatabaseError, IntegrityError
from django.db.models import Q
from django.http import Http404
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.fields import BooleanField, ChoiceField, IntegerField, ListField
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.status import (
    HTTP_201_CREATED,
    HTTP_202_ACCEPTED,
    HTTP_204_NO_CONTENT,
    HTTP_409_CONFLICT,
)
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from core.exceptions import BadRequestException
from logs.views import StandardResultsSetPagination
from organizations.serializers import OrganizationSerializer
from publications.serializers import PlatformSerializer, TitleSerializer
from tags.models import ItemTag, Tag, TagClass, TagScope, TaggingBatch, TaggingBatchState
from tags.permissions import TagClassPermissions, TagPermissions
from tags.serializers import (
    TagClassSerializer,
    TagCreateSerializer,
    TagSerializer,
    TaggingBatchCreateSerializer,
    TaggingBatchSerializer,
)
from tags.tasks import (
    tagging_batch_assign_tag_task,
    tagging_batch_preflight_task,
    tagging_batch_unassign_task,
)


class TagClassViewSet(ModelViewSet):

    queryset = TagClass.objects.none()
    serializer_class = TagClassSerializer
    permission_classes = [IsAuthenticated, TagClassPermissions]

    def get_queryset(self):
        return TagClass.objects.user_accessible_tag_classes(self.request.user)


class TagViewSet(ModelViewSet):

    queryset = Tag.objects.none()
    permission_classes = [IsAuthenticated, TagPermissions]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return TagCreateSerializer
        return TagSerializer

    class ParamSerializer(Serializer):
        item_type = ChoiceField(choices=['title', 'organization', 'platform'], required=False)
        item_id = ListField(child=IntegerField(), required=False)
        assignable_only = BooleanField(required=False)
        scope = ChoiceField(choices=TagScope.choices, required=False)

    def get_queryset(self):
        param_serializer = self.ParamSerializer(data=self.request.query_params)
        param_serializer.is_valid(raise_exception=True)
        params = param_serializer.validated_data
        if params.get('assignable_only', False):
            qs = Tag.objects.user_assignable_tags(self.request.user)
        else:
            qs = Tag.objects.user_accessible_tags(self.request.user)
        if scope := params.get('scope'):
            qs = qs.filter(tag_class__scope=scope)
        qs = qs.select_related('tag_class')

        item_type = params.get('item_type')
        item_id = params.get('item_id')
        if item_id and item_type:
            item_ref_attr = '{0}tag__target_id__in'.format(params['item_type'])
            qs = qs.filter(**{item_ref_attr: params['item_id']}).distinct()
        elif bool(item_type) ^ bool(item_id):
            raise BadRequestException(
                'Either both or none of "item_type" and "item_id" attrs should be present'
            )
        return qs


class TaggedItemViewSet(ReadOnlyModelViewSet):

    pagination_class = StandardResultsSetPagination
    item_list_attr = None

    def user_accessible_items_filter(self) -> Optional[Q]:
        """
        Filters the returned list of target items to only those accessible by the current user.
        """
        return None

    def get_queryset(self):
        tag = get_object_or_404(
            Tag.objects.user_accessible_tags(self.request.user), pk=self.kwargs.get('tag_pk')
        )
        qs = getattr(tag, self.item_list_attr).all()
        if extra_filter := self.user_accessible_items_filter():
            qs = qs.filter(extra_filter)
        return qs

    def user_accessible_target_objects(self):
        qs = self.get_serializer_class().Meta.model.objects.all()
        if extra_filter := self.user_accessible_items_filter():
            qs = qs.filter(extra_filter)
        return qs

    @action(detail=False, methods=['post'])
    def add(self, request, tag_pk):
        tag = get_object_or_404(Tag.objects.user_accessible_tags(self.request.user), pk=tag_pk)
        if not (item_id := self.request.data.get('item_id')):
            raise BadRequestException('"item_id" argument is required')
        obj = get_object_or_404(self.user_accessible_target_objects(), pk=item_id)
        try:
            tag_item = tag.tag(obj, self.request.user)
        except IntegrityError as exc:
            if 'unique_tag_class_for_exclusive' in str(exc):
                raise BadRequestException(
                    {'error': 'Cannot assign more than one tag from an exclusive class to an item'}
                )
            raise BadRequestException({'error': str(exc)})
        return Response({'pk': tag_item.pk}, status=HTTP_201_CREATED)

    @action(detail=False, methods=['delete'])
    def remove(self, request, tag_pk):
        tag = get_object_or_404(Tag.objects.user_accessible_tags(self.request.user), pk=tag_pk)
        if not tag.can_user_assign(request.user):
            raise PermissionDenied('User cannot assing/unassign this tag')
        if not (item_id := self.request.data.get('item_id')):
            raise BadRequestException('"item_id" argument is required')
        obj = get_object_or_404(self.user_accessible_target_objects(), pk=item_id)
        tag_item_class = tag.link_class_from_target(obj)
        try:
            tag_item = tag_item_class.objects.get(tag=tag, target=obj)
        except tag_item_class.DoesNotExist:
            raise BadRequestException('Object is not tagged by this tag')
        else:
            tag_item.delete()
        return Response(status=HTTP_204_NO_CONTENT)


class TaggedTitleViewSet(TaggedItemViewSet):

    serializer_class = TitleSerializer
    item_list_attr = 'titles'


class TaggedPlatformsViewSet(TaggedItemViewSet):

    serializer_class = PlatformSerializer
    item_list_attr = 'platforms'

    def user_accessible_items_filter(self) -> Optional[Q]:
        return Q(pk__in=self.request.user.accessible_platforms())


class TaggedOrganizationsViewSet(TaggedItemViewSet):

    serializer_class = OrganizationSerializer
    item_list_attr = 'organizations'

    def user_accessible_items_filter(self) -> Optional[Q]:
        return Q(pk__in=self.request.user.accessible_organizations())


class TagItemLinksView(APIView):
    class ParamSerializer(Serializer):
        item_type = ChoiceField(choices=TagScope.choices, required=True)
        item_id = ListField(child=IntegerField(), allow_empty=False)

    def get(self, request):
        param_serializer = self.ParamSerializer(data=self.request.query_params)
        param_serializer.is_valid(raise_exception=True)
        params = param_serializer.validated_data
        item_type = params['item_type']
        obj_cls = ItemTag.get_subclass_by_item_type(item_type)
        data = obj_cls.objects.filter(
            tag__in=Tag.objects.user_accessible_tags(request.user),
            tag__tag_class__scope=item_type,
            target_id__in=params['item_id'],
        ).values('tag_id', 'target_id')
        if item_type == TagScope.ORGANIZATION:
            data = data.filter(target_id__in=request.user.accessible_organizations())
        elif item_type == TagScope.PLATFORM:
            data = data.filter(target_id__in=request.user.accessible_platforms())
        return Response(data)


class TaggingBatchViewSet(ModelViewSet):

    queryset = TaggingBatch.objects.none()

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return TaggingBatchCreateSerializer
        return TaggingBatchSerializer

    def get_queryset(self):
        return TaggingBatch.objects.filter(last_updated_by=self.request.user).select_related(
            'tag', 'tag__tag_class', 'tag_class'
        )

    def perform_create(self, serializer):
        super().perform_create(serializer)
        url_base = build_absolute_uri(self.request, '/')
        tagging_batch_preflight_task.delay(serializer.data['pk'], url_base)

    @action(methods=['post'], detail=True, url_name='assign-tags', url_path='assign-tags')
    def assign_tags(self, request, pk):
        try:
            tb = self.get_queryset().select_related().select_for_update(nowait=True).get(pk=pk)
            if tb.state != TaggingBatchState.PREFLIGHT:
                raise BadRequestException(
                    {'error': f'Cannot use batch with state "{tb.state}" to assign tags'}
                )
        except DatabaseError as exc:
            return Response({'error': 'Batch is already being processed'}, status=HTTP_409_CONFLICT)
        except TaggingBatch.DoesNotExist:
            raise Http404({'error': 'Tagging batch not found'})

        # we need to resolve the IDs before submitting them to the task so that we
        # resolve user access and existence of the tags
        if tag_ids_str := request.data.get('tag', ''):
            try:
                tag = Tag.objects.user_assignable_tags(request.user).get(pk=tag_ids_str)
            except Tag.DoesNotExist:
                raise BadRequestException({'error': 'No matching tags to apply were found'})
            tb.state = TaggingBatchState.IMPORTING
            tb.tag = tag
            tb.last_updated_by = request.user
            tb.save()
            url_base = build_absolute_uri(self.request, '/')
            task = tagging_batch_assign_tag_task.apply_async(args=(tb.pk, url_base), countdown=2)
            return Response(
                {
                    'task_id': task.id,
                    'batch': TaggingBatchSerializer(tb, context={"request": request}).data,
                },
                status=HTTP_202_ACCEPTED,
            )
        raise BadRequestException(
            {'error': 'Parameter `tags` with comma separated list of tag IDs is required'}
        )

    @action(methods=['post'], detail=True, url_name='unassign', url_path='unassign')
    def unassign(self, request, pk):
        try:
            tb = self.get_queryset().select_related().select_for_update(nowait=True).get(pk=pk)
            if tb.state != TaggingBatchState.IMPORTED:
                raise BadRequestException(
                    {'error': f'Cannot use batch with state "{tb.state}" to unassign tags'}
                )
        except DatabaseError as exc:
            return Response({'error': 'Batch is already being processed'}, status=HTTP_409_CONFLICT)
        except TaggingBatch.DoesNotExist:
            raise Http404({'error': 'Tagging batch not found'})

        tb.state = TaggingBatchState.UNDOING
        tb.save()
        task = tagging_batch_unassign_task.apply_async(args=(tb.pk,), countdown=2)
        return Response(
            {
                'task_id': task.id,
                'batch': TaggingBatchSerializer(tb, context={"request": request}).data,
            },
            status=HTTP_202_ACCEPTED,
        )
