import pytest
from django.contrib.auth import get_user_model
from django.db.models import Count
from django.utils.timezone import now

from recache.models import CachedQuery, DEFAULT_TIMEOUT
from test_fixtures.entities.users import UserFactory

User = get_user_model()


@pytest.mark.django_db
class TestCachedQuery(object):
    def test_objects_create_from_queryset(self):
        UserFactory.create_batch(1)
        queryset = User.objects.all()
        cq = CachedQuery.objects.create_from_queryset(queryset)
        assert CachedQuery.objects.count() == 1
        assert cq.model.model_class() is User

    def test_objects_create_from_queryset_with_origin(self):
        UserFactory.create_batch(1)
        queryset = User.objects.all()
        cq = CachedQuery.objects.create_from_queryset(queryset, origin='Test')
        assert CachedQuery.objects.count() == 1
        assert cq.model.model_class() is User
        assert cq.origin == 'Test'

    def test_objects_get_for_queryset(self):
        UserFactory.create_batch(1)
        queryset = User.objects.all()
        cq = CachedQuery.objects.create_from_queryset(queryset)
        cq2 = CachedQuery.objects.get_for_queryset(queryset)
        assert cq.pk == cq2.pk

    def test_objects_past_timeout(self):
        UserFactory.create_batch(1)
        queryset = User.objects.all()
        cq = CachedQuery.objects.create_from_queryset(queryset)
        assert CachedQuery.objects.past_timeout().count() == 0
        cq.last_updated = now() - 2 * DEFAULT_TIMEOUT
        cq.save()
        assert CachedQuery.objects.past_timeout().count() == 1

    def test_objects_past_lifetime(self):
        UserFactory.create_batch(1)
        queryset = User.objects.all()
        CachedQuery.objects.create_from_queryset(queryset)
        assert CachedQuery.objects.past_lifetime().count() == 0

    def test_get_fresh_queryset(self):
        UserFactory.create_batch(5)
        queryset = User.objects.all()
        cq = CachedQuery.objects.create_from_queryset(queryset)
        qs2 = cq.get_fresh_queryset()
        assert len(queryset) == 5
        assert len(qs2) == len(queryset)
        assert {u.pk for u in queryset} == {u.pk for u in qs2}

    def test_get_cached_queryset(self):
        UserFactory.create_batch(5)
        queryset = User.objects.all()
        cq = CachedQuery.objects.create_from_queryset(queryset)
        qs2 = cq.get_cached_queryset()
        assert len(queryset) == 5
        assert len(qs2) == len(queryset)
        assert {u.pk for u in queryset} == {u.pk for u in qs2}

    def test_get_cached_queryset_with_change(self):
        UserFactory.create_batch(1)
        queryset = User.objects.all()
        cq = CachedQuery.objects.create_from_queryset(queryset)
        assert cq.get_cached_queryset().count() == 1
        UserFactory.create_batch(3)  # add three more users
        assert cq.get_fresh_queryset().count() == 4, '4 users, newly evaluated queryset'
        assert cq.get_cached_queryset().count() == 1, '1 user, still old cached queryset'
        assert len(cq.query_durations) == 0, 'query was not yet renewed'
        cq.force_renew()
        assert cq.get_cached_queryset().count() == 4, '4 users, updated queryset'
        assert len(cq.query_durations) == 1, 'query was renewed once'

    def test_renew(self):
        UserFactory.create_batch(1)
        queryset = User.objects.all()
        cq = CachedQuery.objects.create_from_queryset(queryset)
        last_updated = cq.last_updated
        cq.renew()
        assert cq.last_updated == last_updated, "should not be renewed bacause it's too early"
        cq.last_updated -= 2 * DEFAULT_TIMEOUT
        cq.renew()
        assert cq.last_updated > last_updated, "should be renewed"
        assert len(cq.query_durations) == 1, 'query was renewed once'

    def test_annotations_work(self):
        UserFactory.create_batch(3)
        queryset = User.objects.values('is_staff').annotate(count=Count('pk'))
        data = list(queryset)
        cq = CachedQuery.objects.create_from_queryset(queryset)
        cq.force_renew()
        data2 = list(cq.get_cached_queryset())
        assert data == data2
