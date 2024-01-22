from rest_framework.fields import ListField


class CompactListField(ListField):
    def get_value(self, dictionary):
        if val := dictionary.get(self.field_name):
            return val.split(",")
        return []
