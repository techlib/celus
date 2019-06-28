import pytest
from django.contrib.auth import get_user_model

from erms.sync import ERMSSyncer
from ..logic.sync import sync_users


@pytest.mark.django_db
class TestUserSync(object):

    user_data = [
        {
            'id': 1,
            'vals': {
                'name@cs': ['Pepa Vonasek']
            },
            'refs': {
                'administrator of': [5]
            }
        },
        {
            'id': 22,
            'vals': {
                'name@cs': ['Lojza Huml']
            },
            'refs': {
                'administrator of': []
            }
        },
        {
            'id': 333,
            'vals': {
                'name@en': ['Jack Sparrow']
            },
        },
    ]

    def test_sync_users(self):
        User = get_user_model()
        assert User.objects.count() == 0
        stats = sync_users(self.user_data)
        assert stats['removed'][0] == 0
        assert stats[ERMSSyncer.Status.NEW] == 3
        assert User.objects.count() == 3
        assert {u.ext_id for u in User.objects.all()} == {1, 22, 333}
