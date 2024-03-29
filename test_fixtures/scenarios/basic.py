import json
from datetime import timedelta

import pytest
from celus_nibbler import conditions as nibbler_conditions
from celus_nibbler import coordinates as nibbler_coordinates
from celus_nibbler import data_headers as nibbler_data_headers
from celus_nibbler import definitions as nibbler_definitions
from celus_nibbler import sources as nibbler_sources
from django.conf import settings
from django.utils import timezone
from logs.models import ReportInterestMetric
from organizations.models import Organization
from rest_framework.test import APIClient
from sushi.models import AttemptStatus

from ..entities.counter_report_types import CounterReportTypeFactory
from ..entities.credentials import CredentialsFactory
from ..entities.data_souces import DataSource, DataSourceFactory
from ..entities.fetchattempts import FetchAttemptFactory
from ..entities.identities import Identity, IdentityFactory
from ..entities.logs import ImportBatchFactory, InterestGroupFactory, MetricFactory
from ..entities.nibbler import ParserDefinitionFactory
from ..entities.organizations import OrganizationFactory
from ..entities.platforms import PlatformFactory
from ..entities.report_types import ReportTypeFactory
from ..entities.scheduler import (
    AutomaticFactory,
    FetchIntentionFactory,
    HarvestFactory,
    SchedulerFactory,
)
from ..entities.users import UserFactory


@pytest.fixture
def users():
    empty = UserFactory(username="empty")
    user1 = UserFactory(username="user1")
    user2 = UserFactory(username="user2")
    master_admin = UserFactory(username="master_admin")
    master_user = UserFactory(username="master_user")
    admin1 = UserFactory(username="admin1")
    admin2 = UserFactory(username="admin2")
    su = UserFactory(username="su", is_superuser=True)
    return locals()


@pytest.fixture
def organizations():
    empty = OrganizationFactory(name="empty")
    # sometimes this fixture is called twice and there is an error because the internal_id is unique,
    # we deal with it here
    try:
        master = Organization.objects.get(internal_id=settings.MASTER_ORGANIZATIONS[0])
    except Organization.DoesNotExist:
        master = OrganizationFactory(name="master", internal_id=settings.MASTER_ORGANIZATIONS[0])
    root = OrganizationFactory(name="root")
    branch = OrganizationFactory(name="branch", parent=root)
    standalone = OrganizationFactory(name="standalone")
    return locals()


@pytest.fixture
def data_sources(organizations):
    api = DataSourceFactory(short_name='api', type=DataSource.TYPE_API)

    brain = DataSourceFactory(
        short_name='brain.celus.net',
        type=DataSource.TYPE_KNOWLEDGEBASE,
        url='https://brain.celus.net',
        token="a" * 64,
    )

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
    master_admin = IdentityFactory(user=users["master_admin"])
    master_user = IdentityFactory(user=users["master_user"])
    admin1 = IdentityFactory(user=users["admin1"])
    admin2 = IdentityFactory(user=users["admin2"])
    su = IdentityFactory(user=users["su"])
    del users
    return locals()


@pytest.fixture
def platforms(data_sources):
    empty = PlatformFactory(name="empty")
    master = PlatformFactory(name="master", source=data_sources["api"])
    brain = PlatformFactory(
        name="brain",
        source=data_sources["brain"],
        knowledgebase={
            "providers": [
                {
                    "assigned_report_types": [
                        {"not_valid_after": None, "not_valid_before": None, "report_type": "JR1"}
                    ],
                    "counter_version": 4,
                    "provider": {
                        "extra": {},
                        "monthly": None,
                        "name": "c4.brain.celus.net",
                        "pk": 10,
                        "url": "http://c4.brain.celus.net",
                        "yearly": None,
                    },
                },
                {
                    "assigned_report_types": [
                        {"not_valid_after": None, "not_valid_before": None, "report_type": "TR"},
                        {"not_valid_after": None, "not_valid_before": None, "report_type": "DR"},
                    ],
                    "counter_version": 5,
                    "provider": {
                        "extra": {},
                        "monthly": None,
                        "name": "c5.brain.celus.net",
                        "pk": 11,
                        "url": "https://c5.brain.celus.net/sushi",
                        "yearly": None,
                    },
                },
            ]
        },
    )

    root = PlatformFactory(name="root", source=data_sources["root"])
    branch = PlatformFactory(name="branch", source=data_sources["branch"])
    standalone = PlatformFactory(name="standalone", source=data_sources["standalone"])
    shared = PlatformFactory(name="shared")
    del data_sources
    return locals()


def make_client(identity: Identity, login: bool = True) -> APIClient:
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
    master_admin = make_client(identities["master_admin"])
    master_user = make_client(identities["master_user"])
    admin1 = make_client(identities["admin1"])
    admin2 = make_client(identities["admin2"])
    su = make_client(identities["su"])
    del identities
    return locals()


@pytest.fixture
def basic1(users, organizations, platforms, data_sources, identities, clients):  # noqa
    # link users and organizations
    users["master_admin"].organizations.add(
        organizations["master"], through_defaults=dict(is_admin=True)
    )
    users["master_user"].organizations.add(
        organizations["master"], through_defaults=dict(is_admin=False)
    )
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
def report_types(data_sources):
    # Counter 5
    tr = ReportTypeFactory(
        name="Counter 5 - Title report", short_name="TR", default_platform_interest=True
    )
    dr = ReportTypeFactory(
        name="Counter 5 - Database report", short_name="DR", default_platform_interest=True
    )
    pr = ReportTypeFactory(name="Counter 5 - Platform report", short_name="PR")
    ir = ReportTypeFactory(name="Counter 5 - Item report", short_name="IR")

    # Counter 4
    br1 = ReportTypeFactory(name="Counter 4 - Book report 1", short_name="BR1")
    br2 = ReportTypeFactory(
        name="Counter 4 - Book report 2", short_name="BR2", default_platform_interest=True
    )
    br3 = ReportTypeFactory(name="Counter 4 - Book report 3", short_name="BR3")

    db1 = ReportTypeFactory(
        name="Counter 4 - Database report 1", short_name="DB1", default_platform_interest=True
    )
    db2 = ReportTypeFactory(name="Counter 4 - Database report 2", short_name="DB2")

    jr1 = ReportTypeFactory(
        name="Counter 4 - Journal report 1", short_name="JR1", default_platform_interest=True
    )
    jr1goa = ReportTypeFactory(
        name="Counter 4 - Journal report 1 Gold Open Access", short_name="JR1GOA"
    )
    jr1a = ReportTypeFactory(name="Counter 4 - Journal report 1 Archive Access", short_name="JR1a")
    jr2 = ReportTypeFactory(name="Counter 4 - Journal report 2", short_name="JR2")
    jr5 = ReportTypeFactory(name="Counter 4 - Journal report 5", short_name="JR5")

    pr1 = ReportTypeFactory(name="Counter 4 - Platform report 1", short_name="PR1")
    mr1 = ReportTypeFactory(name="Counter 4 - Multimedia report 1", short_name="MR1")

    custom1 = ReportTypeFactory(
        name="Custom1", short_name="custom1", source=data_sources['brain'], ext_id=999
    )

    return locals()


@pytest.fixture
def counter_report_types(report_types):
    # counter 5
    tr = CounterReportTypeFactory(
        counter_version=5, code=report_types["tr"].short_name, report_type=report_types["tr"]
    )
    dr = CounterReportTypeFactory(
        counter_version=5, code=report_types["dr"].short_name, report_type=report_types["dr"]
    )
    pr = CounterReportTypeFactory(
        counter_version=5, code=report_types["pr"].short_name, report_type=report_types["pr"]
    )
    ir = CounterReportTypeFactory(
        counter_version=5, code=report_types["ir"].short_name, report_type=report_types["ir"]
    )

    # counter 4
    br1 = CounterReportTypeFactory(
        counter_version=4, code=report_types["br1"].short_name, report_type=report_types["br1"]
    )
    br2 = CounterReportTypeFactory(
        counter_version=4, code=report_types["br2"].short_name, report_type=report_types["br2"]
    )
    br3 = CounterReportTypeFactory(
        counter_version=4, code=report_types["br3"].short_name, report_type=report_types["br3"]
    )

    db1 = CounterReportTypeFactory(
        counter_version=4, code=report_types["db1"].short_name, report_type=report_types["db1"]
    )
    db2 = CounterReportTypeFactory(
        counter_version=4, code=report_types["db2"].short_name, report_type=report_types["db2"]
    )

    jr1 = CounterReportTypeFactory(
        counter_version=4, code=report_types["jr1"].short_name, report_type=report_types["jr1"]
    )
    jr1goa = CounterReportTypeFactory(
        counter_version=4,
        code=report_types["jr1goa"].short_name,
        report_type=report_types["jr1goa"],
    )
    jr1a = CounterReportTypeFactory(
        counter_version=4, code=report_types["jr1a"].short_name, report_type=report_types["jr1a"]
    )
    jr2 = CounterReportTypeFactory(
        counter_version=4, code=report_types["jr2"].short_name, report_type=report_types["jr2"]
    )
    jr5 = CounterReportTypeFactory(
        counter_version=4, code=report_types["jr5"].short_name, report_type=report_types["jr5"]
    )

    pr1 = CounterReportTypeFactory(
        counter_version=4, code=report_types["pr1"].short_name, report_type=report_types["pr1"]
    )

    mr1 = CounterReportTypeFactory(
        counter_version=4, code=report_types["mr1"].short_name, report_type=report_types["mr1"]
    )
    return locals()


@pytest.fixture
def import_batches(report_types):
    pr = ImportBatchFactory(report_type=report_types["pr"])
    return locals()


@pytest.fixture
def credentials(counter_report_types, organizations, platforms):
    standalone_tr = CredentialsFactory(
        organization=organizations["standalone"],
        platform=platforms["standalone"],
        url="https://c5.standalone.example.com/",
        counter_version=5,
    )
    standalone_tr.counter_reports.add(counter_report_types["tr"])

    standalone_br1_jr1 = CredentialsFactory(
        organization=organizations["standalone"],
        platform=platforms["standalone"],
        url="https://c4.standalone.example.com/",
        counter_version=4,
    )
    standalone_br1_jr1.counter_reports.add(counter_report_types["br1"])
    standalone_br1_jr1.counter_reports.add(counter_report_types["jr1"])

    branch_pr = CredentialsFactory(
        organization=organizations["branch"],
        platform=platforms["branch"],
        url="https://c5.branch.example.com/",
        counter_version=5,
    )
    branch_pr.counter_reports.add(counter_report_types["pr"])

    return locals()


@pytest.fixture
def verified_credentials(credentials):
    FetchAttemptFactory(
        credentials=credentials["standalone_tr"],
        status=AttemptStatus.SUCCESS,
        credentials_version_hash=credentials["standalone_tr"].version_hash,
    )
    FetchAttemptFactory(
        credentials=credentials["standalone_br1_jr1"],
        status=AttemptStatus.SUCCESS,
        credentials_version_hash=credentials["standalone_br1_jr1"].version_hash,
    )
    FetchAttemptFactory(
        credentials=credentials["branch_pr"],
        status=AttemptStatus.SUCCESS,
        credentials_version_hash=credentials["branch_pr"].version_hash,
    )


@pytest.fixture
def schedulers(credentials):
    standalone_br1_jr1 = SchedulerFactory(url=credentials["standalone_br1_jr1"].url)
    standalone_tr = SchedulerFactory(url=credentials["standalone_tr"].url)
    branch_pr = SchedulerFactory(url=credentials["branch_pr"].url)
    return locals()


@pytest.fixture
def harvests(users, credentials, counter_report_types, schedulers, organizations, import_batches):
    anonymous = HarvestFactory(
        last_updated_by=None,
        intentions=(
            FetchIntentionFactory.build(
                start_date="2020-01-01",
                end_date="2020-01-31",
                credentials=credentials["standalone_tr"],
                counter_report=counter_report_types["tr"],
                scheduler=schedulers["standalone_tr"],
                when_processed=timezone.now() - timedelta(minutes=1),
                attempt__status=AttemptStatus.DOWNLOAD_FAILED,
            ),
            FetchIntentionFactory.build(
                credentials=credentials["standalone_br1_jr1"],
                counter_report=counter_report_types["br1"],
                attempt=None,
            ),
            FetchIntentionFactory.build(
                start_date="2020-01-01",
                end_date="2020-01-31",
                credentials=credentials["standalone_br1_jr1"],
                counter_report=counter_report_types["jr1"],
                scheduler=schedulers["standalone_br1_jr1"],
                when_processed=timezone.now() - timedelta(minutes=1),
                attempt__status=AttemptStatus.IMPORT_FAILED,
            ),
        ),
    )
    last_queue = anonymous.intentions.order_by('pk').last().queue
    anonymous.intentions.add(
        FetchIntentionFactory(
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["jr1"],
            queue=last_queue,
            previous_intention=anonymous.intentions.filter(queue=last_queue).last(),
            attempt=None,
        ),  # retry fetch attempt
        bulk=False,
    )

    user2 = HarvestFactory(
        last_updated_by=users["user2"],
        intentions=(
            FetchIntentionFactory.build(
                credentials=credentials["standalone_br1_jr1"],
                counter_report=counter_report_types["br1"],
                scheduler=schedulers["standalone_br1_jr1"],
                when_processed=timezone.now() - timedelta(minutes=2),
                start_date="2020-01-01",
                end_date="2020-01-31",
                attempt__status=AttemptStatus.NO_DATA,
            ),
            FetchIntentionFactory.build(
                credentials=credentials["standalone_br1_jr1"],
                counter_report=counter_report_types["jr1"],
                attempt=None,
            ),
        ),
    )

    user1 = HarvestFactory(
        last_updated_by=users["user1"],
        intentions=(
            FetchIntentionFactory.build(
                credentials=credentials["branch_pr"],
                counter_report=counter_report_types["pr"],
                scheduler=schedulers["branch_pr"],
                when_processed=timezone.now() - timedelta(minutes=2),
                start_date="2020-01-01",
                end_date="2020-01-31",
                attempt__status=AttemptStatus.SUCCESS,
                attempt__import_batch=import_batches["pr"],
            ),
            FetchIntentionFactory.build(
                start_date="2020-03-01",
                end_date="2020-03-31",
                credentials=credentials["branch_pr"],
                counter_report=counter_report_types["pr"],
                attempt=None,
            ),
        ),
    )

    automatic = HarvestFactory(
        last_updated_by=None,
        intentions=(
            FetchIntentionFactory.build(
                credentials=credentials["standalone_br1_jr1"],
                counter_report=counter_report_types["br1"],
                start_date="2020-01-01",
                end_date="2020-01-31",
                when_processed=None,
                attempt=None,
            ),
            FetchIntentionFactory.build(
                credentials=credentials["branch_pr"],
                counter_report=counter_report_types["pr"],
                start_date="2020-01-01",
                end_date="2020-01-31",
                when_processed=None,
                duplicate_of=user1.intentions.get(
                    credentials=credentials["branch_pr"],
                    counter_report=counter_report_types["pr"],
                    attempt__isnull=False,
                ),
                attempt=None,
            ),  # dulicate of successfull
        ),
    )
    AutomaticFactory(
        harvest=automatic, month="2020-01-01", organization=organizations["standalone"]
    )

    return locals()


@pytest.fixture
def metrics(report_types, platforms):
    metric1 = MetricFactory(short_name="metric1", name="Metric1")
    metric2 = MetricFactory(short_name="metric2", name="Metric2")
    metric3 = MetricFactory(short_name="metric3", name="Metric3")
    metric4 = MetricFactory(short_name="metric4", name="Metric4")

    return locals()


@pytest.fixture
def interests(report_types, platforms, metrics):
    # Create interest groups
    ig = InterestGroupFactory(short_name='full_text', name='Full Text', position=1)
    InterestGroupFactory(short_name='search', name='Search', position=2)
    InterestGroupFactory(short_name='full_text_denial', name='Denial - full text', position=4)
    InterestGroupFactory(short_name='search_denial', name='Denial - search', position=7)
    InterestGroupFactory(short_name='other', name='Other', position=10)
    InterestGroupFactory(short_name='multimedia', name='Multimedia', position=11)

    for rt_name, metric_names in {
        "jr1": ["metric1", "metric3"],
        "tr": ["metric2", "metric1"],
        "br2": ["metric3"],
    }.items():
        for metric_name in metric_names:
            ReportInterestMetric.objects.create(
                report_type=report_types[rt_name], metric=metrics[metric_name], interest_group=ig
            )

    platforms["standalone"].interest_reports.set([report_types["tr"], report_types["dr"]])
    platforms["branch"].interest_reports.set([report_types["jr1"]])
    return {"ig": ig}


@pytest.fixture
def client_by_user_type(clients, organizations, basic1):
    def fn(user_type):
        if user_type == 'no_user':
            return clients["unauthenticated"], organizations["branch"]
        elif user_type == 'invalid':
            return clients["invalid"], organizations["branch"]
        elif user_type == 'unrelated':
            return clients["user2"], organizations["branch"]
        elif user_type == 'related_user':
            return clients["user1"], organizations["branch"]
        elif user_type == 'related_admin':
            return clients["admin2"], organizations["standalone"]
        elif user_type == 'master_user':
            return clients["master_user"], organizations["branch"]
        elif user_type == 'master_admin':
            return clients["master_admin"], organizations["branch"]
        elif user_type == 'superuser':
            return clients["su"], organizations["branch"]
        else:
            raise ValueError(f'Unsupported user_type: {user_type}')

    return fn


@pytest.fixture
def parser_definitions(data_sources, platforms, metrics, report_types):
    parser1 = ParserDefinitionFactory(
        id=1,
        source=data_sources["brain"],
        definition=json.loads(
            nibbler_definitions.DateBasedDefinition(
                parser_name="parser1",
                data_format=nibbler_data_headers.DataFormatDefinition(
                    name=report_types["custom1"].short_name, id=report_types["custom1"].ext_id
                ),
                platforms=[platforms["brain"].short_name],
                heuristics=nibbler_conditions.AndCondition(
                    conds=[
                        nibbler_conditions.RegexCondition("Title", nibbler_coordinates.Coord(0, 0))
                    ]
                ),
                areas=[
                    nibbler_definitions.DateBasedAreaDefinition(
                        data_headers=nibbler_data_headers.DataHeaders(
                            roles=[
                                nibbler_sources.DateSource(
                                    source=nibbler_coordinates.CoordRange(
                                        nibbler_coordinates.Coord(0, 1),
                                        nibbler_coordinates.Direction.RIGHT,
                                    )
                                )
                            ],
                            data_direction=nibbler_coordinates.Direction.DOWN,
                            data_cells=nibbler_coordinates.CoordRange(
                                nibbler_coordinates.Coord(1, 1), nibbler_coordinates.Direction.RIGHT
                            ),
                        ),
                        titles=nibbler_sources.TitleSource(
                            nibbler_coordinates.CoordRange(
                                nibbler_coordinates.Coord(1, 0), nibbler_coordinates.Direction.DOWN
                            )
                        ),
                        title_ids=[],
                        dimensions=[],
                        metrics=nibbler_sources.MetricSource(
                            source=nibbler_coordinates.Value(value=metrics["metric1"].short_name)
                        ),
                    )
                ],
            ).json()
        ),
    )
    return locals()


__all__ = [
    'basic1',
    'client_by_user_type',
    'clients',
    'counter_report_types',
    'credentials',
    'data_sources',
    'harvests',
    'identities',
    'import_batches',
    'interests',
    'make_client',
    'metrics',
    'organizations',
    'platforms',
    'parser_definitions',
    'report_types',
    'schedulers',
    'users',
    'verified_credentials',
]
