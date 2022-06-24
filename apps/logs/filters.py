from rest_framework import filters


class AccessibleFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if not request.user.is_user_of_master_organization:
            queryset = queryset.filter(organization__in=request.user.accessible_organizations())
        return queryset


class ModifiableFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if not request.user.is_admin_of_master_organization:
            queryset = queryset.filter(organization__in=request.user.accessible_organizations())
        return queryset


class UserFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if user := request.GET.get('user'):
            queryset = queryset.filter(user_id=user)
        return queryset


class OrderByFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        order_by = request.GET.get('order_by', 'created')
        if request.GET.get('desc') in ('true', 1):
            order_by = '-' + order_by
        # ensure that .created is always part of ordering because it is the only value we can
        # be reasonably sure is different between instances
        if order_by != 'created':
            order_by = [order_by, 'created']
        else:
            order_by = [order_by]
        return queryset.order_by(*order_by)
