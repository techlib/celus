from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model

from recache.models import CachedQuery
from recache.util import recache_queryset
from test_fixtures.entities.users import UserFactory

User = get_user_model()


@pytest.mark.django_db
class TestRecacheQueryset:
    """
    Tests the `recache_queryset` util function
    """

    def test_recache_queryset_new(self):
        """
        Tests that uncached queryset lead to creation of new cache and scheduling of its
        renewal
        """
        UserFactory.create_batch(1)
        assert CachedQuery.objects.count() == 0
        with patch('recache.util.renew_cached_query_task') as renewal_task:
            recache_queryset(User.objects.all())
            renewal_task.apply_async.assert_called()
        assert CachedQuery.objects.count() == 1

    def test_recache_queryset_existing_valid(self):
        """
        Tests that existing valid cache is used
        """
        UserFactory.create_batch(1)
        # prepare the cache
        with patch('recache.util.renew_cached_query_task'):
            recache_queryset(User.objects.all())
        assert User.objects.count() == 1
        UserFactory.create_batch(2)  # create more users
        assert User.objects.count() == 3
        assert CachedQuery.objects.count() == 1
        with patch('recache.util.renew_cached_query_task') as renewal_task:
            qs = recache_queryset(User.objects.all())
            renewal_task.apply_async.assert_not_called()
        assert CachedQuery.objects.count() == 1, 'still only one cache object'
        assert qs.count() == 1, 'should keep the old count'
        assert User.objects.count() == 3
        cq = CachedQuery.objects.get()
        assert cq.hit_count == 1, 'the cache should have been hit once'

    def test_recache_queryset_existing_not_too_old(self):
        """
        Tests that existing 'not too old' cache is used but renewal is triggered
        """
        UserFactory.create_batch(1)
        # prepare the cache
        with patch('recache.util.renew_cached_query_task'):
            recache_queryset(User.objects.all())
        assert User.objects.count() == 1
        UserFactory.create_batch(2)  # create more users
        assert User.objects.count() == 3
        assert CachedQuery.objects.count() == 1
        # fix the CachedQuery to no longer be valid but not to be too old
        cq = CachedQuery.objects.get()
        cq.last_updated -= 1.5 * cq.timeout
        cq.save()
        with patch('recache.util.renew_cached_query_task') as renewal_task:
            qs = recache_queryset(User.objects.all())
            renewal_task.apply_async.assert_called()
        assert CachedQuery.objects.count() == 1, 'still only one cache object'
        assert qs.count() == 1, 'should keep the old count'
        assert User.objects.count() == 3

    def test_recache_queryset_existing_but_too_old(self):
        """
        Tests that existing and too old cache is reevaluated immediately before returning
        but also scheduled for later renewal (after timeout is out)
        """
        UserFactory.create_batch(1)
        # prepare the cache
        with patch('recache.util.renew_cached_query_task'):
            recache_queryset(User.objects.all())
        assert User.objects.count() == 1
        UserFactory.create_batch(2)  # create more users
        assert User.objects.count() == 3
        assert CachedQuery.objects.count() == 1
        # fix the CachedQuery to be too old
        cq = CachedQuery.objects.get()
        cq.last_updated -= 3 * cq.timeout
        cq.save()
        with patch('recache.util.renew_cached_query_task') as renewal_task:
            qs = recache_queryset(User.objects.all())
            renewal_task.apply_async.assert_called()
        assert CachedQuery.objects.count() == 1, 'still only one cache object'
        assert qs.count() == 3, 'should have the new count'
        assert User.objects.count() == 3
