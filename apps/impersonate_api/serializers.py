from core.models import User
from organizations.models import UserOrganization
from organizations.serializers import OrganizationShortSerializer
from rest_framework import serializers


class UserOrganization(serializers.ModelSerializer):
    organization = OrganizationShortSerializer(read_only=True)

    class Meta:
        fields = (
            'is_admin',
            'organization',
        )
        model = UserOrganization


class ImpersonateListSerializer(serializers.ModelSerializer):
    current = serializers.BooleanField(required=True)
    real_user = serializers.BooleanField(required=True)
    organizations = UserOrganization(source='userorganization_set', read_only=True, many=True)

    class Meta:
        model = User
        fields = (
            'pk',
            'username',
            'first_name',
            'last_name',
            'organizations',
            'email',
            'current',
            'real_user',
            'is_from_master_organization',
            'is_superuser',
        )

    def to_representation(self, instance):
        request = self.context['request']
        instance.current = request.user.pk == instance.pk
        if request.impersonator:
            instance.real_user = request.impersonator.pk == instance.pk
        else:
            instance.real_user = instance.current

        return super().to_representation(instance)


class ImpersonateSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = tuple()
