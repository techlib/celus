from rest_framework import serializers
from rest_framework.relations import MANY_RELATION_KWARGS


class CommaSeparatedPrimaryKeyListField(serializers.ManyRelatedField):
    def to_internal_value(self, data):
        if type(data) is list and len(data) == 1 and isinstance(data[0], str):
            data = data[0].split(',')
        return super().to_internal_value(data)


class CommaSeparatedPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    @classmethod
    def many_init(cls, *args, **kwargs):
        list_kwargs = {'child_relation': cls(*args, **kwargs)}
        for key in kwargs:
            if key in MANY_RELATION_KWARGS:
                list_kwargs[key] = kwargs[key]
        return CommaSeparatedPrimaryKeyListField(**list_kwargs)
