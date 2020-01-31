from collections import OrderedDict

from django.db.models import Window, Count
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class SmartPageNumberPagination(PageNumberPagination):

    COUNT_ATTR = '_count'

    def __init__(self) -> None:
        super().__init__()
        self.count_ = 0

    def paginate_queryset(self, queryset, request, view=None):
        page_size = self.get_page_size(request)
        if not page_size:
            return None
        try:
            page_number = int(request.query_params.get(self.page_query_param, 1))
        except ValueError:
            page_number = 1
        queryset = queryset.annotate(**{self.COUNT_ATTR: Window(Count('*'))})
        result = queryset[(page_number-1)*page_size:page_number*page_size]
        if result:
            first = result[0]
            if type(first) is dict:
                self.count_ = first.get(self.COUNT_ATTR, 0)
            else:
                self.count_ = getattr(first, self.COUNT_ATTR, 0)
        return result

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('count', self.count_),
            #('next', self.get_next_link()),
            #('previous', self.get_previous_link()),
            ('results', data)
        ]))
