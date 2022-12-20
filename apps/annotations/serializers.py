from core.models import UL_CONS_STAFF, User
from django.utils.log import RequireDebugFalse
from kombu.asynchronous.http.curl import DEFAULT_USER_AGENT
from organizations.models import Organization
from organizations.serializers import OrganizationSerializer
from publications.models import Platform
from publications.serializers import PlatformSerializer, SimplePlatformSerializer
from rest_framework.exceptions import PermissionDenied
from rest_framework.fields import BooleanField, CurrentUserDefault, HiddenField, ReadOnlyField
from rest_framework.relations import PrimaryKeyRelatedField, StringRelatedField
from rest_framework.serializers import ModelSerializer

from .models import Annotation


class AnnotationSerializer(ModelSerializer):

    organization = OrganizationSerializer(read_only=True)
    platform = SimplePlatformSerializer(read_only=True)
    subject = ReadOnlyField()
    organization_id = PrimaryKeyRelatedField(
        source='organization', write_only=True, allow_null=True, queryset=Organization.objects.all()
    )
    platform_id = PrimaryKeyRelatedField(
        source='platform', write_only=True, allow_null=True, queryset=Platform.objects.all()
    )
    can_edit = BooleanField(read_only=True)
    submitter = HiddenField(default=CurrentUserDefault())
    author = StringRelatedField()

    class Meta:
        model = Annotation
        fields = (
            'pk',
            'organization_id',
            'platform_id',
            'subject',
            'subject_en',
            'subject_cs',
            'short_message',
            'short_message_en',
            'short_message_cs',
            'message',
            'message_en',
            'message_cs',
            'start_date',
            'end_date',
            'organization',
            'platform',
            'level',
            'can_edit',
            'submitter',
            'author',
        )
        extra_kwargs = {'subject_en': {'allow_blank': False}}

    def update(self, instance: Annotation, validated_data):
        # in patch updates, the submitter field might not be present
        submitter = validated_data.pop('submitter', None) or self.context['request'].user
        if not instance.can_edit(submitter):
            raise PermissionDenied('User is not allowed to edit this object - it is locked.')
        result = super().update(instance, validated_data)  # type: Annotation
        return self._adjust_permissions(result, submitter)

    def create(self, validated_data):
        submitter = validated_data.pop('submitter')  # type: User
        result = super().create(validated_data)
        return self._adjust_permissions(result, submitter)

    @classmethod
    def _adjust_permissions(cls, instance: Annotation, submitter: User):
        instance.author = submitter
        instance.owner_level = (
            submitter.organization_relationship(instance.organization_id)
            if instance.organization_id
            else UL_CONS_STAFF
        )
        # we do not want to set the level too high in order for the staff to be able to edit it
        if instance.owner_level > UL_CONS_STAFF:
            instance.owner_level = UL_CONS_STAFF
        instance.save()
        instance.can_edit = instance.can_edit(submitter)
        return instance
