import pytest
from django.urls import reverse

from test_fixtures.scenarios.basic import (  # noqa - fixtures
    basic1,
    clients,
    counter_report_types,
    credentials,
    data_sources,
    harvests,
    identities,
    import_batches,
    organizations,
    platforms,
    report_types,
    schedulers,
    users,
)


@pytest.mark.django_db
class TestImpersonateAPI:
    @pytest.mark.parametrize(
        "client,count",
        (
            ("su", 8),  # admin{1,2}, user{1,2}, empty, master_{admin,user}, su
            ("master_admin", 7),  # admin{1,2}, user{1,2}, empty, master_{admin,user}
            ("master_user", 0),
            ("admin1", 0),
            ("admin2", 0),
            ("user1", 0),
            ("user2", 0),
            ("unauthenticated", 0),
            ("invalid", 0),
        ),
    )
    def test_list(self, basic1, clients, client, count):
        response = clients[client].get(reverse("impersonate-list"))
        if count:
            assert response.status_code == 200
            assert len(response.data) == count
            for user in response.data:
                if user["username"] == client:
                    assert user["real_user"] is True
                    assert user["current"] is True
                else:
                    assert user["real_user"] is False
                    assert user["current"] is False
        else:
            assert response.status_code in [403, 401]

    @pytest.mark.parametrize(
        "from_client,to_user,success",
        (
            ("su", "user1", True),
            ("su", "master_admin", True),
            ("master_admin", "user1", True),
            ("master_admin", "master_user", True),
            ("master_admin", "admin1", True),
            ("master_admin", "su", False),
            ("master_user", "user1", False),
            ("admin1", "user1", False),
            ("admin1", "master_admin", False),
            ("admin1", "su", False),
        ),
    )
    def test_complex(self, basic1, clients, users, from_client, to_user, success):
        response = clients[from_client].put(
            reverse("impersonate-detail", kwargs={"pk": users[to_user].pk})
        )
        if success:
            assert response.status_code == 200

            response = clients[from_client].get(reverse("impersonate-list"))
            assert response.status_code == 200
            assert (
                clients[from_client].get(reverse("user_api_view")).data["impersonator"] is not None
            )
            for user in response.data:
                if user["username"] == from_client:
                    assert user["real_user"] is True
                    assert user["current"] is False
                elif user["username"] == to_user:
                    assert user["real_user"] is False
                    assert user["current"] is True
                else:
                    assert user["real_user"] is False
                    assert user["current"] is False

            # Switch back
            response = clients[from_client].put(
                reverse("impersonate-detail", kwargs={"pk": users[from_client].pk})
            )
            assert response.status_code == 200
            for user in response.data:
                if user["username"] == from_client:
                    assert user["real_user"] is True
                    assert user["current"] is True
                else:
                    assert user["real_user"] is False
                    assert user["current"] is False

            assert clients[from_client].get(reverse("user_api_view")).data["impersonator"] is None

        else:

            assert response.status_code in [404, 403]
            # try to list to see whether something has changed
            response = clients[from_client].get(reverse("impersonate-list"))
            assert clients[from_client].get(reverse("user_api_view")).data["impersonator"] is None
            if response.status_code == 200:
                # Should remain untouched
                for user in response.data:
                    if user["username"] == from_client:
                        assert user["real_user"] is True
                        assert user["current"] is True
                    else:
                        assert user["real_user"] is False
                        assert user["current"] is False
            else:
                assert response.status_code == 403, "not allowed to list"
