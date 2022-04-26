from functools import cached_property

from django.core.exceptions import BadRequest
from rest_framework.exceptions import PermissionDenied
from rest_framework.fields import (
    HiddenField,
    CurrentUserDefault,
    SerializerMethodField,
    ReadOnlyField,
)
from rest_framework.serializers import ModelSerializer

from tags.models import Tag, TagClass, TaggingBatch


class TagClassSerializer(ModelSerializer):

    user_can_modify = SerializerMethodField()

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
        tag = super().create(validated_data)
        return tag

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
        tag = super().update(instance, validated_data)
        return tag


class TagSerializer(ModelSerializer):

    tag_class = TagClassSerializer()
    user_can_assign = SerializerMethodField()

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
            'user_can_assign',
        )

    def get_user_can_assign(self, tag: Tag):
        return tag.pk in self._user_assignable_tag_ids

    @cached_property
    def _user_assignable_tag_ids(self):
        return set(
            Tag.objects.user_assignable_tags(self.context['request'].user).values_list(
                'pk', flat=True
            )
        )


class TagCreateSerializer(ModelSerializer):

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
        )

    def update(self, instance: Tag, validated_data):
        # generic modify permissions are handled on the viewset level by `permission_classes`
        # here we handle only the specific cases
        if 'tag_class' in validated_data and validated_data['tag_class'] != instance.tag_class:
            raise BadRequest('Changing tag_class of existing tag is not supported')
        # the CurrentUserDefault() does not seem to be used for updates
        validated_data['owner'] = self.context['request'].user
        tag = super().update(instance, validated_data)
        return tag

    def create(self, validated_data):
        user = self.context['request'].user
        # the following test cannot be handled by permissions on viewset level, so we do it here
        if (tc := validated_data['tag_class']) not in TagClass.objects.user_accessible_tag_classes(
            user
        ):
            raise PermissionDenied(f'User cannot add tags to class "{tc}"')
        tag = super().create(validated_data)
        return tag


class _TaggingBatchBaseSerializer(ModelSerializer):

    preflight = ReadOnlyField()

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
        )


class TaggingBatchSerializer(_TaggingBatchBaseSerializer):

    tag = TagSerializer(read_only=True)
    tag_class = TagClassSerializer(read_only=True)


class TaggingBatchCreateSerializer(_TaggingBatchBaseSerializer):

    last_updated_by = HiddenField(default=CurrentUserDefault())
