from django.db.models import Q
from rest_framework.viewsets import ReadOnlyModelViewSet

from annotations.models import Annotation
from annotations.serializers import AnnotationSerializer


class AnnotationsViewSet(ReadOnlyModelViewSet):

    queryset = Annotation.objects.all()
    serializer_class = AnnotationSerializer

    def get_queryset(self):
        query_args = []
        exclude_params = {}
        for param in ('platform', 'report_type', 'organization', 'title'):
            value = self.request.query_params.get(param)
            if value:
                # we filter to include those with specified value or with this value null
                query_args.append(Q(**{param+'_id': value}) | Q(**{param+'__isnull': True}))
        start_date = self.request.query_params.get('start_date')
        if start_date:
            exclude_params['end_date__lte'] = start_date
        end_date = self.request.query_params.get('end_date')
        if end_date:
            exclude_params['start_date__gte'] = end_date
        return Annotation.objects.filter(*query_args).exclude(**exclude_params).\
            select_related('organization', 'platform', 'report_type', 'title')

