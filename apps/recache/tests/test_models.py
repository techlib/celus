import django
import pytest
from django.contrib.auth import get_user_model
from django.db.models import Count
from django.utils.timezone import now
from recache.models import DEFAULT_LIFETIME, DEFAULT_TIMEOUT, CachedQuery, RenewalError

from test_fixtures.entities.users import UserFactory

User = get_user_model()


@pytest.mark.django_db
class TestCachedQuery:
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
        cq.last_updated = now() - DEFAULT_TIMEOUT
        cq.save()
        assert CachedQuery.objects.past_timeout().count() == 1
        assert CachedQuery.objects.past_timeout().first() == cq

    def test_objects_past_lifetime(self):
        UserFactory.create_batch(1)
        queryset = User.objects.all()
        cq = CachedQuery.objects.create_from_queryset(queryset)
        assert CachedQuery.objects.past_lifetime().count() == 0
        cq.last_queried = now() - DEFAULT_LIFETIME
        cq.save()
        assert CachedQuery.objects.past_lifetime().count() == 1
        assert CachedQuery.objects.past_lifetime().first() == cq
        assert CachedQuery.objects.past_lifetime().delete()[0] == 1

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

    def test_renew_with_different_django_version(self):
        """
        Test that when a cached query for older django version is renewed the `django_version`
        attr is updated.
        """
        UserFactory.create_batch(1)
        queryset = User.objects.all()
        cq = CachedQuery.objects.create_from_queryset(queryset)
        fake_django_version = '2.2.foobar'
        cq.django_version = fake_django_version
        cq.save()
        cq.renew()
        assert cq.django_version != fake_django_version, "django_version should change"
        assert cq.django_version == django.get_version()
        assert CachedQuery.objects.count() == 1, 'there should be only one cache'

    def test_renew_with_clashing_django_version(self):
        """
        Test that when a cached query for older django version is renewed and there is already a
        cache for the current version, the current cache gets deleted.
        This is to allow 'upgrade' of caches to newer django but at the same time prevent
        unique together related errors
        """
        UserFactory.create_batch(1)
        queryset = User.objects.all()
        cq_orig = CachedQuery.objects.create_from_queryset(queryset)
        fake_django_version = '2.2.foobar'
        cq_orig.django_version = fake_django_version
        cq_orig.save()
        # now create the clashing current CachedQuery
        cq_new = CachedQuery.objects.create_from_queryset(queryset)
        assert CachedQuery.objects.count() == 2, 'there should be the old and the new cache'
        # let's try to renew the old one
        with pytest.raises(RenewalError):
            cq_orig.renew()
        assert cq_orig.django_version == fake_django_version, "django_version should be the same"
        assert cq_new.django_version == django.get_version()
        assert CachedQuery.objects.count() == 2, 'there should still be the old and the new cache'
