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
from ..entities.identities import IdentityFactory, Identity
from ..entities.users import UserFactory
from ..entities.organizations import OrganizationFactory
from ..entities.platforms import PlatformFactory
from ..entities.data_souces import DataSourceFactory, DataSource


@pytest.fixture
def users():
    empty = UserFactory(username="empty")
    user1 = UserFactory(username="user1")
    user2 = UserFactory(username="user2")
    master = UserFactory(username="master")
    admin1 = UserFactory(username="admin1")
    admin2 = UserFactory(username="admin2")
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


def make_client(identity: Identity) -> APIClient:
    client = APIClient()
    client.force_login(identity.user)
    return client


@pytest.fixture
def clients(identities):
    unauthenticated = APIClient()
    user1 = make_client(identities["user1"])
    user2 = make_client(identities["user2"])
    master = make_client(identities["master"])
    admin1 = make_client(identities["admin1"])
    admin2 = make_client(identities["admin2"])
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
