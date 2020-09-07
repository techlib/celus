"""
Users:
    TODO description

Organizations:
    TODO description

Platforms:
    TODO description

"""

import pytest

from rest_framework.test import APIClient
from django.conf import settings
from ..entities.counter_report_types import CounterReportTypeFactory
from ..entities.credentials import CredentialsFactory
from ..entities.data_souces import DataSourceFactory, DataSource
from ..entities.identities import IdentityFactory, Identity
from ..entities.organizations import OrganizationFactory
from ..entities.platforms import PlatformFactory
from ..entities.report_types import ReportTypeFactory
from ..entities.users import UserFactory


@pytest.fixture
def users():
    empty = UserFactory(username="empty")
    user1 = UserFactory(username="user1")
    user2 = UserFactory(username="user2")
    master = UserFactory(username="master")
    admin1 = UserFactory(username="admin1")
    admin2 = UserFactory(username="admin2")
    su = UserFactory(username="su", is_superuser=True)
    return locals()


@pytest.fixture
def organizations():
    empty = OrganizationFactory(name="empty")
    master = OrganizationFactory(name="master", internal_id=settings.MASTER_ORGANIZATIONS[0])
    root = OrganizationFactory(name="root")
    branch = OrganizationFactory(name="branch", parent=root)
    standalone = OrganizationFactory(name="standalone")
    return locals()


@pytest.fixture
def data_sources(organizations):
    api = DataSourceFactory(short_name='api', type=DataSource.TYPE_API)
    root = DataSourceFactory(
        short_name="root", type=DataSource.TYPE_ORGANIZATION, organization=organizations["root"]
    )
    branch = DataSourceFactory(
        short_name="branch", type=DataSource.TYPE_ORGANIZATION, organization=organizations["branch"]
    )
    standalone = DataSourceFactory(
        short_name="standalone",
        type=DataSource.TYPE_ORGANIZATION,
        organization=organizations["standalone"],
    )
    del organizations
    return locals()


@pytest.fixture
def identities(users):
    user1 = IdentityFactory(user=users["user1"])
    user2 = IdentityFactory(user=users["user2"])
    master = IdentityFactory(user=users["master"])
    admin1 = IdentityFactory(user=users["admin1"])
    admin2 = IdentityFactory(user=users["admin2"])
    su = IdentityFactory(user=users["su"])
    del users
    return locals()


@pytest.fixture
def platforms(data_sources):
    empty = PlatformFactory(name="empty")
    master = PlatformFactory(name="master", source=data_sources["api"])
    root = PlatformFactory(name="root", source=data_sources["root"])
    branch = PlatformFactory(name="branch", source=data_sources["branch"])
    standalone = PlatformFactory(name="standalone", source=data_sources["standalone"])
    shared = PlatformFactory(name="shared")
    del data_sources
    return locals()


def make_client(identity: Identity, login: bool = False) -> APIClient:
    client = APIClient()
    client.defaults[settings.EDUID_IDENTITY_HEADER] = identity
    if login:
        client.force_login(identity.user)
    return client


@pytest.fixture
def clients(identities):
    unauthenticated = APIClient()
    invalid = make_client("invalid@celus.test", False)
    user1 = make_client(identities["user1"])
    user2 = make_client(identities["user2"])
    master = make_client(identities["master"])
    admin1 = make_client(identities["admin1"])
    admin2 = make_client(identities["admin2"])
    su = make_client(identities["su"])
    del identities
    return locals()


@pytest.fixture
def basic1(users, organizations, platforms, data_sources, identities, clients):  # noqa
    # link users and organizations
    users["master"].organizations.add(organizations["master"], through_defaults=dict(is_admin=True))
    users["admin1"].organizations.add(organizations["root"], through_defaults=dict(is_admin=True))
    users["admin2"].organizations.add(
        organizations["standalone"], through_defaults=dict(is_admin=True)
    )
    users["user1"].organizations.add(organizations["branch"], through_defaults=dict(is_admin=False))
    users["user2"].organizations.add(
        organizations["standalone"], through_defaults=dict(is_admin=False)
    )

    return locals()


@pytest.fixture
def report_types():
    # Counter 5
    tr = ReportTypeFactory(name="Counter 5 - Title report", short_name="TR")
    dr = ReportTypeFactory(name="Counter 5 - Database report", short_name="DR")
    pr = ReportTypeFactory(name="Counter 5 - Platform report", short_name="PR")

    # Counter 4
    br1 = ReportTypeFactory(name="Counter 4 - Book report 1", short_name="BR1")
    br2 = ReportTypeFactory(name="Counter 4 - Book report 2", short_name="BR2")
    br3 = ReportTypeFactory(name="Counter 4 - Book report 3", short_name="BR3")

    db1 = ReportTypeFactory(name="Counter 4 - Database report 1", short_name="DB1")
    db2 = ReportTypeFactory(name="Counter 4 - Database report 2", short_name="DB2")

    jr1 = ReportTypeFactory(name="Counter 4 - Journal report 1", short_name="JR1")
    jr1goa = ReportTypeFactory(
        name="Counter 4 - Journal report 1 Gold Open Access", short_name="JR1GOA"
    )
    jr1a = ReportTypeFactory(name="Counter 4 - Journal report 1 Archive Access", short_name="JR1a")
    jr2 = ReportTypeFactory(name="Counter 4 - Journal report 2", short_name="JR2")
    jr5 = ReportTypeFactory(name="Counter 4 - Journal report 5", short_name="JR5")

    pr1 = ReportTypeFactory(name="Counter 4 - Platform report 1", short_name="PR1")

    return locals()


@pytest.fixture
def counter_report_types(report_types):
    # counter 5
    tr = CounterReportTypeFactory(
        counter_version=5, code=report_types["tr"].short_name, report_type=report_types["tr"],
    )
    dr = CounterReportTypeFactory(
        counter_version=5, code=report_types["dr"].short_name, report_type=report_types["dr"],
    )
    pr = CounterReportTypeFactory(
        counter_version=5, code=report_types["pr"].short_name, report_type=report_types["pr"],
    )

    # counter 4
    br1 = CounterReportTypeFactory(
        counter_version=4, code=report_types["br1"].short_name, report_type=report_types["br1"],
    )
    br2 = CounterReportTypeFactory(
        counter_version=4, code=report_types["br2"].short_name, report_type=report_types["br2"],
    )
    br3 = CounterReportTypeFactory(
        counter_version=4, code=report_types["br3"].short_name, report_type=report_types["br3"],
    )

    db1 = CounterReportTypeFactory(
        counter_version=4, code=report_types["db1"].short_name, report_type=report_types["db1"],
    )
    db2 = CounterReportTypeFactory(
        counter_version=4, code=report_types["db2"].short_name, report_type=report_types["db2"],
    )

    # counter 4
    jr1 = CounterReportTypeFactory(
        counter_version=4, code=report_types["jr1"].short_name, report_type=report_types["jr1"],
    )
    jr1goa = CounterReportTypeFactory(
        counter_version=4,
        code=report_types["jr1goa"].short_name,
        report_type=report_types["jr1goa"],
    )
    jr1a = CounterReportTypeFactory(
        counter_version=4, code=report_types["jr1a"].short_name, report_type=report_types["jr1a"],
    )
    jr2 = CounterReportTypeFactory(
        counter_version=4, code=report_types["jr2"].short_name, report_type=report_types["jr2"],
    )
    jr5 = CounterReportTypeFactory(
        counter_version=4, code=report_types["jr5"].short_name, report_type=report_types["jr5"],
    )

    pr1 = CounterReportTypeFactory(
        counter_version=4, code=report_types["pr1"].short_name, report_type=report_types["pr1"],
    )
    return locals()


@pytest.fixture
def credentials(counter_report_types, organizations, platforms):
    standalone_tr = CredentialsFactory(
        organization=organizations["standalone"],
        platform=platforms["standalone"],
        url="https://c5.standalone.example.com/",
        counter_version=5,
    )
    standalone_tr.active_counter_reports.add(counter_report_types["tr"])

    standalone_br1_jr1 = CredentialsFactory(
        organization=organizations["standalone"],
        platform=platforms["standalone"],
        url="https://c4.standalone.example.com/",
        counter_version=4,
    )
    standalone_br1_jr1.active_counter_reports.add(counter_report_types["br1"])
    standalone_br1_jr1.active_counter_reports.add(counter_report_types["jr1"])
    return locals()
