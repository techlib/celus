from rest_framework import filters


class PkMultiValueFilterBackend(filters.BaseFilterBackend):
    """
    Filter that allows selection by a list of primary keys
    """

    filter_field = 'pk'
    query_param = 'pks'

    def filter_queryset(self, request, queryset, view):
        pks = request.query_params.get(self.query_param)
        if pks:
            keys = pks.split(',')
            queryset = queryset.filter(**{f'{self.filter_field}__in': keys})
        return queryset
