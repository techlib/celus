from rest_framework import serializers

from events.models import Event, UserEvent


class EventSerializer(serializers.ModelSerializer):
    read = serializers.BooleanField(read_only=True)  # created in a query

    class Meta:
        model = Event
        fields = (
            "pk",
            "title",
            "description",
            "expiration_date",
            "importance",
            "category",
            "platform",
            "created",
            "read",
        )


class UserEventSerializer(serializers.ModelSerializer):
    """
    This serializer is intended to be used for single UserEvent instances when sending them
    to the frontend via websockets.
    """

    event = EventSerializer(read_only=True)
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = UserEvent
        fields = (
            "pk",
            "event",
            "read",
            "user_id",
            "unread_count",
        )

    def get_unread_count(self, obj: UserEvent):
        return UserEvent.objects.filter(user=obj.user, read=False).count()
