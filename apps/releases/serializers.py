from rest_framework import serializers


class LocalizedText(serializers.Serializer):
    en = serializers.CharField(required=True)
    cs = serializers.CharField(required=False, allow_null=True)


class LinkSerializer(serializers.Serializer):
    title = LocalizedText(required=True)
    link = serializers.URLField(required=True)


class ReleaseSerializer(serializers.Serializer):
    version = serializers.CharField(required=True)
    title = LocalizedText(required=True)
    text = LocalizedText(required=False, allow_null=True)
    is_new_feature = serializers.BooleanField(default=False)
    is_update = serializers.BooleanField(default=False)
    is_bug_fix = serializers.BooleanField(default=False)
    links = LinkSerializer(required=False, many=True, allow_null=True)
