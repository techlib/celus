import json
from datetime import date

import pytest
from core.fake_data import DataSourceFactory, UserFactory
from core.logic.maximus_sync import (
    get_organizations,
    get_platforms,
    get_relations,
    get_sushi_credentials,
    get_users,
)
from core.models import UL_ORG_ADMIN, User
from organizations.fake_data import OrganizationFactory
from organizations.models import Organization
from publications.fake_data import PlatformFactory
from sushi.fake_data import CounterReportTypeFactory
from sushi.models import AttemptStatus, SushiCredentials, SushiFetchAttempt


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

    @pytest.mark.django_db
    def test_get_platforms(self):
        ds = DataSourceFactory.create(type=2)
        platforms = PlatformFactory.create_batch(2, source=ds)
        check = [
            {
                "ext_id": p.id,
                "short_name": p.short_name,
                "name": p.name,
                "source": str(ds),
                "source_type": ds.get_type_display(),
                "counter_registry_id": None,
            }
            for p in platforms
        ]
        for d in json.loads(json.dumps(get_platforms())):
            assert d in check

    @pytest.mark.django_db
    def test_get_sushi_credentials(self):
        o1 = OrganizationFactory.create()
        platforms = PlatformFactory.create_batch(2)
        ct = (
            CounterReportTypeFactory.create(),
            CounterReportTypeFactory.create(code='X1'),
            CounterReportTypeFactory.create(code='Y2'),
        )
        s = [
            SushiCredentials.objects.create(
                organization=o1,
                platform=platforms[i],
                url="http://example.com/",
                counter_version=5,
                customer_id="1234",
                lock_level=UL_ORG_ADMIN,
            )
            for i in range(2)
        ]
        s[0].counter_reports.add(ct[0], ct[1])
        s[1].counter_reports.add(ct[1], ct[2])
        SushiFetchAttempt.objects.create(
            status=AttemptStatus.SUCCESS,
            credentials=s[0],
            counter_report=ct[0],
            start_date=date.today(),
            end_date=date.today(),
            checksum="abc",
            file_size=123,
        )
        check = [
            {
                "ext_id": s[i].id,
                "organization": o1.id,
                "platform": platforms[i].id,
                "url": "http://example.com/",
                "counter_version": 5,
                "customer_id": "1234",
                "counter_reports": [ct[i].code, ct[i + 1].code],
                "api_key": "",
                "enabled": True,
                "extra_params": {},
                "http_username": "",
                "http_password": "",
                "lock_level": 300,
                "outside_consortium": False,
                "requestor_id": "",
                "broken": None,
                "verified": not bool(i),
            }
            for i in range(2)
        ]
        for d in json.loads(json.dumps(get_sushi_credentials())):
            assert d in check
