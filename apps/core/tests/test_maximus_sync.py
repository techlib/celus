import json

import pytest
from core.logic.maximus_sync import get_organizations, get_relations, get_users
from core.models import User
from organizations.models import Organization

from test_fixtures.entities.organizations import OrganizationFactory
from test_fixtures.entities.users import UserFactory


@pytest.mark.django_db
class TestMaximusSync:
    def test_get_organizations(self):
        assert get_organizations() == []

        o1 = Organization.objects.create(
            name="Alphabet", short_name="Abc", raw_data_import_enabled=True
        )
        check = (
            {
                "ext_id": o1.id,
                "name": "Alphabet",
                "short_name": "Abc",
                "raw_data_import_enabled": True,
            },
        )
        out = json.loads(json.dumps(get_organizations()))
        assert len(out) == len(check)
        for d in out:
            assert d in check

        o2 = Organization.objects.create(
            name="Spring Library", short_name="Spring Library", raw_data_import_enabled=False
        )
        check = (
            check[0],
            {
                "ext_id": o2.id,
                "name": "Spring Library",
                "short_name": "Spring Library",
                "raw_data_import_enabled": False,
            },
        )
        out = json.loads(json.dumps(get_organizations()))
        assert len(out) == len(check)
        for d in out:
            assert d in check

    def test_get_users(self):
        assert get_users() == []

        u1 = User.objects.create(username="a")
        check = (
            {"ext_id": u1.id, "username": "a", "first_name": "", "last_name": "", "email": ""},
        )
        out = json.loads(json.dumps(get_users()))
        assert len(out) == len(check)
        for d in out:
            assert d in check

        u2 = User.objects.create(
            username="b", first_name="Bob", last_name="Bobster", email="bob@bobster.com"
        )
        check = (
            {"ext_id": u1.id, "username": "a", "first_name": "", "last_name": "", "email": ""},
            {
                "ext_id": u2.id,
                "username": "b",
                "first_name": "Bob",
                "last_name": "Bobster",
                "email": "bob@bobster.com",
            },
        )
        out = json.loads(json.dumps(get_users()))
        assert len(out) == len(check)
        for d in out:
            assert d in check

    def test_get_relations(self):
        usr = UserFactory.create_batch(3)
        org = OrganizationFactory.create_batch(2)

        assert get_relations() == []

        org[0].users.add(usr[1], through_defaults={'is_admin': True})
        org[1].users.add(usr[1], through_defaults={'is_admin': True})
        org[0].users.add(usr[2])
        check = (
            {"user": usr[1].id, "organization": org[0].id, "is_admin": True},
            {"user": usr[1].id, "organization": org[1].id, "is_admin": True},
            {"user": usr[2].id, "organization": org[0].id, "is_admin": False},
        )
        for d in json.loads(json.dumps(get_relations())):
            assert d in check

        org[0].users.add(usr[0], through_defaults={'is_admin': True})
        org[0].users.remove(usr[1])
        org[1].users.remove(usr[1])
        check = (
            {"user": usr[0].id, "organization": org[0].id, "is_admin": True},
            {"user": usr[2].id, "organization": org[0].id, "is_admin": False},
        )
        for d in json.loads(json.dumps(get_relations())):
            assert d in check
