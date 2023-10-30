from functools import cached_property

from core.serializers import UserSimpleSerializer
from django.core.exceptions import BadRequest
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.fields import (
    BooleanField,
    CurrentUserDefault,
    HiddenField,
    IntegerField,
    SerializerMethodField,
)
from rest_framework.serializers import ModelSerializer

from tags.models import Tag, TagClass, TaggingAttempt, TaggingBatch, TagScope


class TagClassSerializer(ModelSerializer):
    user_can_modify = SerializerMethodField()
    user_score = SerializerMethodField()
    hidden = BooleanField(default=False, read_only=True)

    class Meta:
        model = TagClass
        fields = (
            'pk',
            'name',
            'scope',
            'exclusive',
            'text_color',
            'bg_color',
            'desc',
            'can_modify',
            'can_create_tags',
            'owner',
            'owner_org',
            'default_tag_can_see',
            'default_tag_can_assign',
            'user_can_modify',
            'user_score',
            'hidden',
        )

    def get_user_can_modify(self, tc: TagClass):
        return tc.pk in self._user_modifiable_class_ids

    @cached_property
    def _user_modifiable_class_ids(self):
        """
        caching reduces the number of db queries done per request to 1
        """
        return set(
            TagClass.objects.user_modifiable_tag_classes(self.context['request'].user).values_list(
                'pk', flat=True
            )
        )

    def create(self, validated_data):
        for permission_attr in (
            'can_modify',
            'can_create_tags',
            'default_tag_can_see',
            'default_tag_can_assign',
        ):
            if (cat := validated_data.get(permission_attr)) is not None:
                if not TagClass.can_set_access_level(
                    self.context['request'].user, cat, organization=validated_data.get('owner_org')
                ):
                    raise PermissionDenied(
                        f'User cannot create tag class with access level "{cat}"'
                    )
        if 'owner' not in validated_data:
            validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)

    def update(self, instance: TagClass, validated_data):
        if 'owner' not in validated_data:
            validated_data['owner'] = self.context['request'].user
        # check that we are not updating stuff that cannot be changed after creation
        # scope cannot be changed at all
        if (scope := validated_data.get('scope')) and scope != instance.scope:
            raise BadRequest('Scope of a class cannot be changed after its creation')
        # exclusivity can only be relaxed, not tightened
        if (
            (exclusive := validated_data.get('exclusive')) is not None
            and exclusive != instance.exclusive
            and exclusive
        ):
            raise BadRequest('Class cannot be made exclusive after its creation')
        # check permissions
        for permission_attr in (
            'can_modify',
            'can_create_tags',
            'default_tag_can_see',
            'default_tag_can_assign',
        ):
            if (cat := validated_data.get(permission_attr)) is not None:
                if not TagClass.can_set_access_level(
                    self.context['request'].user,
                    cat,
                    organization=validated_data.get('owner_org', instance.owner_org),
                ):
                    raise PermissionDenied(f'User cannot change tag class access level to "{cat}"')
        return super().update(instance, validated_data)

    def get_user_score(self, tc: TagClass):
        return self._tag_class_user_scores.get(tc.pk, 0)

    @cached_property
    def _tag_class_user_scores(self) -> dict:
        return {
            tc.pk: tc.user_score
            for tc in TagClass.objects.annotate_user_score(self.context['request'].user).only('pk')
        }


class TagSerializer(ModelSerializer):
    user_can_assign = SerializerMethodField()
    user_can_modify = SerializerMethodField()
    last_updated_by = HiddenField(default=CurrentUserDefault())
    owner = HiddenField(default=CurrentUserDefault())

    class Meta:
        model = Tag
        fields = (
            'pk',
            'tag_class',
            'name',
            'text_color',
            'bg_color',
            'desc',
            'can_see',
            'can_assign',
            'owner',
            'owner_org',
            'last_updated_by',
            'user_can_assign',
            'user_can_modify',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tc_serializer = None

    def get_user_can_assign(self, tag: Tag):
        return tag.pk in self._user_assignable_tag_ids

    @cached_property
    def _user_assignable_tag_ids(self):
        return set(
            Tag.objects.user_assignable_tags(self.context['request'].user).values_list(
                'pk', flat=True
            )
        )

    def get_user_can_modify(self, tag: Tag):
        return tag.pk in self._user_modifiable_ids

    @cached_property
    def _user_modifiable_ids(self):
        """
        caching reduces the number of db queries done per request to 1
        """
        return set(
            Tag.objects.user_modifiable_tags(self.context['request'].user).values_list(
                'pk', flat=True
            )
        )

    def update(self, instance: Tag, validated_data):
        # generic modify permissions are handled on the viewset level by `permission_classes`
        # here we handle only the specific cases
        if 'tag_class' in validated_data and validated_data['tag_class'] != instance.tag_class:
            raise BadRequest('Changing tag_class of existing tag is not supported')
        # the CurrentUserDefault() does not seem to be used for updates
        validated_data['owner'] = self.context['request'].user
        return super().update(instance, validated_data)

    def create(self, validated_data):
        user = self.context['request'].user
        # the following test cannot be handled by permissions on viewset level, so we do it here
        if (tc := validated_data['tag_class']) not in TagClass.objects.user_accessible_tag_classes(
            user
        ):
            raise PermissionDenied(f'User cannot add tags to class "{tc}"')
        return super().create(validated_data)

    def to_representation(self, instance):
        # this is a trick how to ensure that the serializer will support primary keys
        # for tag_class on input, but will always return full objects on output
        # we also make sure to create the serializer only once, so that
        # it can use per-serializer caching used to reduce the number of db queries
        data = super().to_representation(instance)
        if instance.tag_class:
            if not self.tc_serializer:
                self.tc_serializer = TagClassSerializer(context=self.context)
            data['tag_class'] = self.tc_serializer.to_representation(instance.tag_class)
        if instance.owner_id:
            data['owner'] = instance.owner_id
        return data


class TaggingAttemptSerializer(ModelSerializer):
    class Meta:
        model = TaggingAttempt
        fields = (
            'pk',
            'operation',
            'recognized_columns',
            'rows_total',
            'rows_no_match',
            'rows_no_tag',
            'tag_stats',
            'unique_matched_titles',
            'already_tagged_titles',
            'tagged_titles',
            'exclusively_tagged_titles',
            'created',
            'last_updated',
            'error',
        )


class TaggingBatchSerializer(ModelSerializer):
    preflight = TaggingAttemptSerializer(source='last_preflight', read_only=True)
    postflight = TaggingAttemptSerializer(source='last_import', read_only=True)
    last_updated_by = UserSimpleSerializer(read_only=True)
    import_count = IntegerField(read_only=True)

    class Meta:
        model = TaggingBatch
        fields = (
            'pk',
            'source_file',
            'annotated_file',
            'preflight',
            'postflight',
            'tag',
            'tag_class',
            'state',
            'last_updated_by',
            'created',
            'last_updated',
            'import_count',
            'reprocess_after',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # we need to cache the serializers to avoid repeated db queries created by to_representation
        # the reason is that the serializers cache some values, but if we create a new serializer
        # for each object, the cache is not used
        self.tag_serializer = None
        self.tc_serializer = None

    def validate(self, attrs):
        result = super().validate(attrs)
        if not self.partial:
            # when partial is true, only some attrs are given, so we cannot expect tag or tag_class
            # to be present
            if attrs.get('tag') and attrs.get('tag_class'):
                raise ValidationError('Cannot set both tag and tag_class')
            if not attrs.get('tag') and not attrs.get('tag_class'):
                raise ValidationError('Either tag or tag_class must be set')
        user = self.context['request'].user
        if tag := attrs.get('tag'):
            if not tag.can_user_assign(user):
                raise PermissionDenied(f'User cannot assign tag "{tag}"')
            if tag.tag_class.scope != TagScope.TITLE:
                raise ValidationError('Tag must have scope "title"')
        elif tc := attrs.get('tag_class'):  # type: TagClass
            if not TagClass.objects.user_assignable_tag_classes(user).filter(pk=tc.pk).exists():
                raise PermissionDenied(f'User cannot assign tags from tag class "{tc}"')
            if tc.scope != TagScope.TITLE:
                raise ValidationError('Tag class must have scope "title"')
        return result

    def to_representation(self, instance):
        # this is a trick how to ensure that the serializer will support primary keys
        # for tag and tag_class on input, but will always return full objects on output
        data = super().to_representation(instance)
        # here we cache the serializers to avoid repeated db queries
        if not self.tag_serializer:
            self.tag_serializer = TagSerializer(context=self.context)
        if not self.tc_serializer:
            self.tc_serializer = TagClassSerializer(context=self.context)
        if instance.tag:
            data['tag'] = self.tag_serializer.to_representation(instance.tag)
        if instance.tag_class:
            data['tag_class'] = self.tc_serializer.to_representation(instance.tag_class)
        return data


class TaggingBatchCreateSerializer(TaggingBatchSerializer):
    last_updated_by = HiddenField(default=CurrentUserDefault())
