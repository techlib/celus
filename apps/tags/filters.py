from rest_framework import filters
from tags.models import TagScope


class TagClassScopeFilter(filters.BaseFilterBackend):
    """
    Filter that allows selection of tag scope
    """

    filter_field = 'scope'
    query_param = 'scope'

    def filter_queryset(self, request, queryset, view):
        scope = request.query_params.get(self.query_param)
        if scope and scope in TagScope.values:
            queryset = queryset.filter(**{f'{self.filter_field}': scope})
        return queryset
