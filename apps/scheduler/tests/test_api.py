import json
from datetime import date
from itertools import product

import pytest
from core.logic.dates import last_month, month_end
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone
from hcube.api.models.aggregation import Sum as HSum
from logs.cubes import AccessLogCube, ch_backend
from logs.models import AccessLog, ImportBatch
from organizations.models import UserOrganization
from scheduler import tasks
from scheduler.models import Automatic, FetchIntention, Harvest
from sushi.models import AttemptStatus
from sushi.models import BrokenCredentialsMixin as BS
from sushi.models import CounterReportsToCredentials, SushiFetchAttempt
from test_fixtures.entities.credentials import CredentialsFactory
from test_fixtures.entities.fetchattempts import FetchAttemptFactory
from test_fixtures.entities.logs import ImportBatchFullFactory
from test_fixtures.entities.scheduler import FetchIntentionFactory
from test_fixtures.scenarios.basic import (
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
    verified_credentials,
)


@pytest.mark.django_db
class TestHarvestAPI:
    def test_list(self, basic1, clients, harvests):
        url = reverse('harvest-list')
        resp = clients["master_admin"].get(url, {})
        assert resp.status_code == 200
        data = resp.json()["results"]
        assert len(data) == 6
        assert data[0]["pk"] < data[1]["pk"] < data[2]["pk"], "default sort by pk asc"

        # stats
        assert data[0]["stats"] == {"total": 3, "planned": 2, "attempt_count": 2, "working": 0}
        assert data[1]["stats"] == {"total": 2, "planned": 1, "attempt_count": 1, "working": 0}
        assert data[2]["stats"] == {"total": 1, "planned": 1, "attempt_count": 0, "working": 0}
        assert data[3]["stats"] == {"total": 2, "planned": 1, "attempt_count": 1, "working": 0}
        assert data[4]["stats"] == {"total": 1, "planned": 1, "attempt_count": 0, "working": 0}
        assert data[5]["stats"] == {"total": 2, "planned": 1, "attempt_count": 0, "working": 0}

        # start and end dates
        assert data[0]["start_date"] == "2020-01-01"
        assert data[0]["end_date"] == "2020-01-31"
        assert data[1]["start_date"] == "2020-01-01"
        assert data[1]["end_date"] == "2020-01-31"
        assert data[2]["start_date"] == last_month().strftime("%Y-%m-%d")
        assert data[2]["end_date"] == month_end(last_month()).strftime("%Y-%m-%d")
        assert data[3]["start_date"] == "2020-01-01"
        assert data[3]["end_date"] == "2020-03-31"
        assert data[4]["start_date"] == last_month().strftime("%Y-%m-%d")
        assert data[4]["end_date"] == month_end(last_month()).strftime("%Y-%m-%d")
        assert data[5]["start_date"] == "2020-01-01"
        assert data[5]["end_date"] == "2020-01-31"

        # last processed fetch intention
        assert data[0]["last_processed"] is not None
        assert data[1]["last_processed"] is not None
        assert data[2]["last_processed"] is None
        assert data[3]["last_processed"] is not None
        assert data[4]["last_processed"] is None
        assert data[5]["last_processed"] is None

        # test broken
        assert data[0]["broken"] == 0
        assert data[1]["broken"] == 0
        assert data[2]["broken"] == 0
        assert data[3]["broken"] == 0
        assert data[4]["broken"] == 0
        assert data[5]["broken"] == 0

    @pytest.mark.parametrize(
        ['column', 'desc'], list(product(['pk', 'created'], ['true', 'false']))
    )
    def test_list_order_by(self, basic1, clients, harvests, desc, column):
        url = reverse('harvest-list')
        resp = clients["master_admin"].get(url, {'order_by': column, 'desc': desc})
        assert resp.status_code == 200
        data = resp.json()["results"]
        assert len(data) == 6
        if desc == 'true':
            assert (
                data[0][column] > data[1][column] > data[2][column]
            ), "desc sorting should be active"
        else:
            assert (
                data[0][column] < data[1][column] < data[2][column]
            ), "asc sorting should be active"

    def test_list_filter_finished(self, basic1, clients, harvests):

        # remove unfinished from one harvest
        harvests["anonymous"].intentions.filter(when_processed__isnull=True).delete()

        url = reverse('harvest-list')
        # test finished filter
        resp = clients["master_admin"].get(url + "?finished=yes", {})
        assert resp.status_code == 200
        data1 = resp.json()["results"]
        assert len(data1) == 1

        resp = clients["master_admin"].get(url + "?finished=no", {})
        assert resp.status_code == 200
        data2 = resp.json()["results"]
        assert len(data2) == 5

        resp = clients["master_admin"].get(url + "?finished=working", {})
        assert resp.status_code == 200
        data3 = resp.json()["results"]
        assert len(data3) == 0

        assert data1[0]["pk"] != data2[0]["pk"]
        assert data1[0]["pk"] != data2[1]["pk"]

    def test_list_filter_automatic(self, basic1, clients, harvests):

        url = reverse('harvest-list')
        # test finished filter
        resp = clients["master_admin"].get(url + "?automatic=1", {})
        assert resp.status_code == 200
        data1 = resp.json()["results"]
        assert len(data1) == 3

        resp = clients["master_admin"].get(url + "?automatic=0", {})
        assert resp.status_code == 200
        data2 = resp.json()["results"]
        assert len(data2) == 3

        assert data1[0]["pk"] != data2[0]["pk"]
        assert data1[0]["pk"] != data2[1]["pk"]

    def test_list_filter_broken(self, basic1, clients, harvests, credentials, counter_report_types):

        # broken credentials
        fi = FetchIntentionFactory(
            harvest=harvests["automatic"],
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["br1"],
            when_processed=timezone.now(),
        )
        credentials["standalone_br1_jr1"].broken = BS.BROKEN_HTTP
        credentials["standalone_br1_jr1"].first_broken_attempt = fi.attempt
        credentials["standalone_br1_jr1"].save()

        url = reverse('harvest-list')
        # test finished filter
        resp = clients["master_admin"].get(url + "?broken=1", {})
        assert resp.status_code == 200
        data1 = resp.json()["results"]
        assert len(data1) == 2

        resp = clients["master_admin"].get(url + "?broken=0", {})
        assert resp.status_code == 200
        data2 = resp.json()["results"]
        assert len(data2) == 3

    def test_list_filter_month(self, basic1, clients, harvests):

        url = reverse('harvest-list')
        # test finished filter
        resp = clients["master_admin"].get(url + "?month=2020-01", {})
        assert resp.status_code == 200
        data1 = resp.json()["results"]
        assert len(data1) == 4

        resp = clients["master_admin"].get(url + "?month=2020-03", {})
        assert resp.status_code == 200
        data2 = resp.json()["results"]
        assert len(data2) == 1

    def test_list_filter_platforms(self, basic1, clients, harvests, platforms):
        url = reverse('harvest-list')
        resp = clients["master_admin"].get(url + f"?platforms={platforms['branch'].pk}", {})
        assert resp.status_code == 200
        data1 = resp.json()["results"]
        assert len(data1) == 3

        url += f"?platforms={platforms['branch'].pk},{platforms['standalone'].pk}"
        resp = clients["master_admin"].get(url, {},)
        assert resp.status_code == 200
        data2 = resp.json()["results"]
        assert len(data2) == 6

    def test_get(self, basic1, clients, harvests):
        url = reverse('harvest-detail', args=(harvests["anonymous"].pk,))
        resp = clients["master_admin"].get(url, {})
        assert resp.status_code == 200
        data = resp.json()
        assert data["stats"] == {"total": 3, "planned": 2, "attempt_count": 2, "working": 0}
        assert len(data["intentions"]) == 3

        url = reverse('harvest-detail', args=(harvests["user1"].pk,))
        resp = clients["master_admin"].get(url, {})
        assert resp.status_code == 200
        data = resp.json()
        assert data["stats"] == {"total": 2, "planned": 1, "attempt_count": 1, "working": 0}
        assert len(data["intentions"]) == 2

        url = reverse('harvest-detail', args=(harvests["automatic"].pk,))
        resp = clients["master_admin"].get(url, {})
        assert resp.status_code == 200
        data = resp.json()
        assert data["stats"] == {"total": 2, "planned": 1, "attempt_count": 0, "working": 0}
        assert len(data["intentions"]) == 2

        url = reverse('harvest-detail', args=(harvests["user2"].pk,))
        resp = clients["master_admin"].get(url, {})
        assert resp.status_code == 200
        data = resp.json()
        assert data["stats"] == {"total": 2, "planned": 1, "attempt_count": 1, "working": 0}
        assert len(data["intentions"]) == 2

    @pytest.mark.django_db(transaction=True)
    def test_create(
        self, basic1, clients, harvests, credentials, counter_report_types, users, monkeypatch
    ):
        url = reverse('harvest-list')
        stored_intentions_count = FetchIntention.objects.count()
        planned_urls = set()

        def mocked_trigger_scheduler(
            url, fihish,
        ):
            planned_urls.add(url)

        monkeypatch.setattr(tasks.trigger_scheduler, 'delay', mocked_trigger_scheduler)

        resp = clients["master_admin"].post(
            url,
            json.dumps(
                {
                    "intentions": [
                        {
                            "credentials": credentials["standalone_tr"].pk,
                            "counter_report": counter_report_types["tr"].pk,
                            "start_date": "2020-03-01",
                            "end_date": "2020-03-31",
                        },
                        {
                            "credentials": credentials["standalone_br1_jr1"].pk,
                            "counter_report": counter_report_types["br1"].pk,
                            "start_date": "2020-03-01",
                            "end_date": "2020-03-31",
                        },
                    ]
                }
            ),
            content_type='application/json',
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["stats"] == {"total": 2, "planned": 2, "attempt_count": 0, "working": 0}
        assert len(data["intentions"]) == 2
        assert data["last_updated_by"] == users["master_admin"].pk
        assert stored_intentions_count + 2 == FetchIntention.objects.count()
        assert FetchIntention.objects.order_by('-pk')[0].priority >= FetchIntention.PRIORITY_NOW
        assert FetchIntention.objects.order_by('-pk')[1].priority >= FetchIntention.PRIORITY_NOW

        assert planned_urls == {
            credentials["standalone_tr"].url,
            credentials["standalone_br1_jr1"].url,
        }

    @pytest.mark.parametrize(
        "user,length",
        (
            ("master_admin", 6),
            ("master_user", 0),
            ("admin1", 0),
            ("admin2", 2),
            ("user1", 1),
            ("user2", 1),
        ),
    )
    def test_list_filtering(self, basic1, harvests, clients, user, length):
        url = reverse('harvest-list')
        resp = clients[user].get(url, {})
        assert resp.status_code == 200
        data = resp.json()["results"]
        assert len(data) == length

    @pytest.mark.parametrize(
        "user,anonymous_status,automatic_status,user1_status",
        (
            ("master_admin", 200, 200, 200),
            ("master_user", 404, 404, 404),
            ("admin1", 404, 404, 404),
            ("admin2", 404, 200, 404),
            ("user1", 404, 404, 200),
            ("user2", 404, 404, 404),
        ),
    )
    def test_get_permissions(
        self, basic1, harvests, clients, user, anonymous_status, automatic_status, user1_status
    ):
        url = reverse('harvest-detail', args=(harvests["anonymous"].pk,))
        resp = clients[user].get(url, {})
        assert resp.status_code == anonymous_status

        url = reverse('harvest-detail', args=(harvests["automatic"].pk,))
        resp = clients[user].get(url, {})
        assert resp.status_code == automatic_status

        url = reverse('harvest-detail', args=(harvests["user1"].pk,))
        resp = clients[user].get(url, {})
        assert resp.status_code == user1_status

    def test_create_permission(
        self, basic1, harvests, clients, credentials, counter_report_types, monkeypatch
    ):
        url = reverse('harvest-list')

        def mocked_trigger_scheduler(
            url, fihish,
        ):
            pass

        monkeypatch.setattr(tasks.trigger_scheduler, 'delay', mocked_trigger_scheduler)

        # can create harvests if user is an organization member
        resp = clients["user2"].post(
            url,
            json.dumps(
                {
                    "intentions": [
                        {
                            "credentials": credentials["standalone_tr"].pk,
                            "counter_report": counter_report_types["tr"].pk,
                            "start_date": "2020-03-01",
                            "end_date": "2020-03-31",
                        },
                        {
                            "credentials": credentials["standalone_br1_jr1"].pk,
                            "counter_report": counter_report_types["br1"].pk,
                            "start_date": "2020-03-01",
                            "end_date": "2020-03-31",
                        },
                    ]
                }
            ),
            content_type='application/json',
        )
        assert resp.status_code == 201

        # missing permissions for a single credentials
        resp = clients["user2"].post(
            url,
            json.dumps(
                {
                    "intentions": [
                        {
                            "credentials": credentials["branch_pr"].pk,
                            "counter_report": counter_report_types["pr"].pk,
                            "start_date": "2020-03-01",
                            "end_date": "2020-03-31",
                        },
                        {
                            "credentials": credentials["standalone_br1_jr1"].pk,
                            "counter_report": counter_report_types["br1"].pk,
                            "start_date": "2020-03-01",
                            "end_date": "2020-03-31",
                        },
                    ]
                }
            ),
            content_type='application/json',
        )
        assert resp.status_code == 403

    def test_create_empty(self, clients):
        url = reverse('harvest-list')
        resp = clients["master_admin"].post(
            url, json.dumps({"intentions": []}), content_type='application/json',
        )
        assert resp.status_code == 400, "At least one intention has to be used"

    def test_create_broken(self, basic1, clients, counter_report_types, credentials, monkeypatch):
        url = reverse('harvest-list')

        def mocked_trigger_scheduler(
            url, fihish,
        ):
            pass

        monkeypatch.setattr(tasks.trigger_scheduler, 'delay', mocked_trigger_scheduler)

        # entire credentails broken
        attempt_tr = FetchAttemptFactory(
            credentials=credentials["standalone_tr"], counter_report=counter_report_types["tr"]
        )
        credentials["standalone_tr"].broken = BS.BROKEN_HTTP
        credentials["standalone_tr"].first_broken_attempt = attempt_tr
        credentials["standalone_tr"].save()

        # broken report type
        attempt_br1 = FetchAttemptFactory(
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["br1"],
        )
        cr2c_br1 = CounterReportsToCredentials.objects.get(
            credentials=credentials["standalone_br1_jr1"], counter_report__code="BR1"
        )
        cr2c_br1.broken = BS.BROKEN_SUSHI
        cr2c_br1.first_broken_attempt = attempt_br1
        cr2c_br1.save()

        # only jr1 ok
        resp = clients["master_admin"].post(
            url,
            json.dumps(
                {
                    "intentions": [
                        {
                            "credentials": credentials["branch_pr"].pk,
                            "counter_report": counter_report_types["pr"].pk,
                            "start_date": "2020-03-01",
                            "end_date": "2020-03-31",
                        },
                        {
                            "credentials": credentials["standalone_br1_jr1"].pk,
                            "counter_report": counter_report_types["jr1"].pk,
                            "start_date": "2020-03-01",
                            "end_date": "2020-03-31",
                        },
                    ]
                }
            ),
            content_type='application/json',
        )
        assert resp.status_code == 201

        # tr included -> broken
        resp = clients["master_admin"].post(
            url,
            json.dumps(
                {
                    "intentions": [
                        {
                            "credentials": credentials["standalone_tr"].pk,
                            "counter_report": counter_report_types["tr"].pk,
                            "start_date": "2020-03-01",
                            "end_date": "2020-03-31",
                        },
                        {
                            "credentials": credentials["standalone_br1_jr1"].pk,
                            "counter_report": counter_report_types["jr1"].pk,
                            "start_date": "2020-03-01",
                            "end_date": "2020-03-31",
                        },
                    ]
                }
            ),
            content_type='application/json',
        )
        assert resp.status_code == 400

        # br1 included -> broken
        resp = clients["master_admin"].post(
            url,
            json.dumps(
                {
                    "intentions": [
                        {
                            "credentials": credentials["standalone_br1_jr1"].pk,
                            "counter_report": counter_report_types["jr1"].pk,
                            "start_date": "2020-03-01",
                            "end_date": "2020-03-31",
                        },
                        {
                            "credentials": credentials["standalone_br1_jr1"].pk,
                            "counter_report": counter_report_types["br1"].pk,
                            "start_date": "2020-03-01",
                            "end_date": "2020-03-31",
                        },
                    ]
                }
            ),
            content_type='application/json',
        )
        assert resp.status_code == 400

    def test_automatic(
        self, basic1, clients, credentials, verified_credentials,
    ):
        # remove all automatic harvests
        Harvest.objects.filter(automatic__isnull=False).delete()

        url = reverse('harvest-list')
        resp = clients["master_admin"].get(url, {})
        assert resp.status_code == 200
        data = resp.json()["results"]
        assert len(data) == 0

        # this should create automatic harvests
        Automatic.update_for_this_month()

        url = reverse('harvest-list')
        resp = clients["master_admin"].get(url, {})
        assert resp.status_code == 200
        data = resp.json()["results"]
        assert len(data) == 2
        assert data[0]['automatic'].keys() == {"pk", "month", "organization"}
        assert data[1]['automatic'].keys() == {"pk", "month", "organization"}

        # check whether atomic is are present in details
        url = reverse('harvest-detail', args=(data[0]['pk'],))
        resp = clients["master_admin"].get(url, {})
        assert resp.status_code == 200
        data = resp.json()
        assert data["automatic"] is not None
        assert 'month' in data["automatic"]
        assert 'organization' in data["automatic"]
        assert 'pk' in data['automatic']['organization']
        assert 'name' in data['automatic']['organization']
        assert 'short_name' in data['automatic']['organization']

    def test_automatic_no_verified(self, basic1, clients, credentials):
        url = reverse('harvest-list')
        resp = clients["master_admin"].get(url, {})
        assert resp.status_code == 200
        data = resp.json()["results"]
        assert len(data) == 0

        # this should create automatic harvests
        Automatic.update_for_this_month()

        url = reverse('harvest-list')
        resp = clients["master_admin"].get(url, {})
        assert resp.status_code == 200
        data = resp.json()["results"]
        assert len(data) == 0


@pytest.mark.django_db()
class TestHarvestFetchIntentionAPI:
    def test_list(self, basic1, clients, harvests):

        url = reverse('harvest-intention-list', args=(harvests["anonymous"].pk,))
        resp = clients["master_admin"].get(url, {})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        assert "broken_credentials" in data[0]
        assert data[2]["previous_intention"] is not None
        assert all("canceled" in record for record in data)

        url = reverse('harvest-intention-list', args=(harvests["user1"].pk,))
        resp = clients["master_admin"].get(url, {})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert "broken_credentials" in data[0]
        assert all("canceled" in record for record in data)

        url = reverse('harvest-intention-list', args=(harvests["automatic"].pk,))
        resp = clients["master_admin"].get(url, {})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert "broken_credentials" in data[0]
        duplicate = data[1]["duplicate_of"]
        assert duplicate["attempt"] is not None
        assert all("canceled" in record for record in data)

    @pytest.mark.parametrize(
        "user,anonymous_status,user1_status",
        (
            ("master_admin", 200, 200),
            ("master_user", 404, 404),
            ("user1", 404, 200),
            ("user2", 404, 404),
        ),
    )
    def test_list_permissions(
        self, basic1, harvests, clients, user, anonymous_status, user1_status
    ):
        url = reverse('harvest-intention-list', args=(harvests["anonymous"].pk,))
        resp = clients[user].get(url, {})
        assert resp.status_code == anonymous_status

        url = reverse('harvest-intention-list', args=(harvests["user1"].pk,))
        resp = clients[user].get(url, {})
        assert resp.status_code == user1_status

    def test_get(self, basic1, clients, harvests):
        url = reverse(
            'harvest-intention-detail',
            args=(harvests["anonymous"].pk, harvests["anonymous"].latest_intentions.first().pk),
        )
        resp = clients["master_admin"].get(url, {})
        assert resp.status_code == 200
        data = resp.json()
        assert "broken_credentials" in data

        url = reverse(
            'harvest-intention-detail',
            args=(harvests["user1"].pk, harvests["anonymous"].latest_intentions.first().pk),
        )

        resp = clients["master_admin"].get(url, {})
        assert resp.status_code == 404

    def test_retry(self, basic1, clients, harvests):
        """
        Tests that when a fetch intention creates a new one as a retry, access to the old one
        will be preserved
        """
        url = reverse(
            'harvest-intention-detail',
            args=(harvests['anonymous'].pk, harvests['anonymous'].latest_intentions.first().pk),
        )
        resp = clients["master_admin"].get(url, {})
        assert resp.status_code == 200
        # create new intention by setting .pk to None and saving
        old_pk = resp.json()['pk']
        intention = FetchIntention.objects.get(pk=old_pk)
        intention.pk = None
        intention.data_not_ready_retry = 1
        intention.attempt = None
        intention.save()
        intention.queue.end = intention
        intention.queue.save()

        # try to get old and new intentions via get
        resp = clients['master_admin'].get(
            reverse('harvest-intention-detail', args=(harvests['anonymous'].pk, intention.pk),)
        )
        assert resp.status_code == 200, 'new intention should be reachable'
        resp = clients['master_admin'].get(
            reverse('harvest-intention-detail', args=(harvests['anonymous'].pk, old_pk),)
        )
        assert resp.status_code == 200, 'old intention should be reachable as well'

        # try to get old and new intentions via list
        resp = clients['master_admin'].get(
            reverse('harvest-intention-list', args=(harvests['anonymous'].pk,),)
        )
        assert resp.status_code == 200
        assert old_pk not in [e["pk"] for e in resp.json()], 'by default old should be hidden'

        resp = clients['master_admin'].get(
            reverse('harvest-intention-list', args=(harvests['anonymous'].pk,),) + '?list_all=1'
        )
        assert resp.status_code == 200
        assert old_pk in [e["pk"] for e in resp.json()], '"list_all" param will show all'

    @pytest.mark.parametrize(
        "user,anonymous_status,user1_status",
        (
            ("master_admin", 200, 200),
            ("master_user", 404, 404),
            ("user1", 404, 200),
            ("user2", 404, 404),
        ),
    )
    def test_get_permissions(self, basic1, harvests, clients, user, anonymous_status, user1_status):
        url = reverse(
            'harvest-intention-detail',
            args=(harvests["anonymous"].pk, harvests["anonymous"].latest_intentions.first().pk),
        )
        resp = clients[user].get(url, {})
        assert resp.status_code == anonymous_status

        url = reverse(
            'harvest-intention-detail',
            args=(harvests["user1"].pk, harvests["user1"].latest_intentions.first().pk),
        )
        resp = clients[user].get(url, {})
        assert resp.status_code == user1_status

    @pytest.mark.parametrize(
        "user,processed,status,planned",
        (
            ("master_admin", False, 200, True),
            ("master_admin", True, 400, False),
            ("master_user", False, 404, False),
            ("master_user", False, 404, False),
            ("user1", False, 200, True),
            ("user1", True, 400, False),
            ("user2", True, 404, False),
            ("user2", False, 404, False),
        ),
    )
    def test_trigger(
        self, basic1, harvests, clients, monkeypatch, user, processed, status, planned
    ):
        if processed:
            intention = harvests["user1"].latest_intentions.first()
        else:
            intention = harvests["user1"].latest_intentions.last()

        url = reverse('harvest-intention-trigger', args=(intention.harvest.pk, intention.pk),)

        planned_urls = set()

        def mocked_trigger_scheduler(
            url, fihish,
        ):
            planned_urls.add(url)

        monkeypatch.setattr(tasks.trigger_scheduler, 'delay', mocked_trigger_scheduler)

        resp = clients[user].post(url, {})
        assert resp.status_code == status, "status code matches"
        assert planned == bool(planned_urls), "schedulers triggering was planned"

    @pytest.mark.parametrize(
        "user,cancelable,status",
        (
            ("master_admin", True, 200),
            ("master_admin", False, 400),
            ("master_user", True, 404),
            ("master_user", False, 404),
            ("user1", True, 200),
            ("user1", False, 400),
            ("user2", False, 404),
            ("user2", True, 404),
        ),
    )
    def test_cancel(self, basic1, harvests, clients, user, cancelable, status):
        if cancelable:
            intention = harvests["user1"].intentions.latest_intentions().order_by('pk')[1]
        else:
            intention = harvests["user1"].intentions.latest_intentions().order_by('pk')[0]

        url = reverse('harvest-intention-cancel', args=(intention.harvest.pk, intention.pk),)

        resp = clients[user].post(url, {})
        assert resp.status_code == status, "status code matches"

        intention.refresh_from_db()
        if cancelable and status // 100 == 2:
            assert intention.canceled is True
        else:
            assert intention.canceled is False


@pytest.mark.django_db()
class TestFetchIntentionAPI:
    @pytest.mark.parametrize(
        ['user', 'status_code'],
        [
            ['unauthenticated', 401],
            ['invalid', 401],
            ['user1', 200],
            ['user2', 404],
            ['admin1', 200],
            ['admin2', 404],
            ['master_admin', 200],
            ['master_user', 200],
            ['su', 200],
        ],
    )
    def test_detail(
        self,
        basic1,
        clients,
        organizations,
        platforms,
        counter_report_types,
        harvests,
        credentials,
        user,
        status_code,
    ):
        """
        Check whether displaying detail about fetch attempts works properly
        """
        intention = harvests["user1"].intentions.latest_intentions().order_by('pk')[0]
        url = reverse('intention-detail', args=(intention.pk,))
        resp = clients[user].get(url)
        assert resp.status_code == status_code

    @pytest.mark.parametrize(['attempt_count'], [(1,), (2,), (10,)])
    def test_list(self, admin_client, attempt_count, django_assert_max_num_queries):
        cr = CredentialsFactory()
        FetchAttemptFactory.create_batch(attempt_count, credentials=cr)
        FetchIntentionFactory.create_batch(attempt_count, credentials=cr, attempt__credentials=cr)
        with django_assert_max_num_queries(9):  # even 10 attempts should be under 10 requests
            resp = admin_client.get(reverse('intention-list'))
        assert resp.status_code == 200
        assert len(resp.json()['results']) == attempt_count

    def test_list_filtering(self, admin_client):
        cr = CredentialsFactory()
        cr2 = CredentialsFactory()
        assert cr.platform_id != cr2.platform_id
        FetchIntentionFactory.create_batch(3, credentials=cr, attempt__credentials=cr)
        fi = FetchIntentionFactory(
            credentials=cr2, attempt__credentials=cr2, when_processed=timezone.now(),
        )
        fi.refresh_from_db()
        FetchIntentionFactory.create_batch(
            29,
            credentials=cr2,
            attempt__credentials=cr2,
            queue=fi.queue,
            when_processed=timezone.now(),
        )

        # no mode set (should be the same as all mode
        resp = admin_client.get(reverse('intention-list'))
        assert resp.status_code == 200
        assert len(resp.json()['results']) == 4, "no mode no platform filter"
        resp = admin_client.get(reverse('intention-list'), {'platform': cr.platform_id})
        assert resp.status_code == 200
        assert len(resp.json()['results']) == 3, "no mode with platform filter"

        # mode all
        resp = admin_client.get(reverse('intention-list'), {'mode': 'all'})
        assert resp.status_code == 200
        assert len(resp.json()['results']) == 33, "mode all no platform filter"
        resp = admin_client.get(
            reverse('intention-list'), {'platform': cr.platform_id, 'mode': 'all'}
        )
        assert resp.status_code == 200
        assert len(resp.json()['results']) == 3, "mode all with platform filter"

        # mode current
        resp = admin_client.get(reverse('intention-list'), {"mode": "current"})
        assert resp.status_code == 200
        assert len(resp.json()['results']) == 4, "no platform filter"
        resp = admin_client.get(
            reverse('intention-list'), {'platform': cr.platform_id, "mode": "current"}
        )
        assert resp.status_code == 200
        assert len(resp.json()['results']) == 3, "with platform filter"

        # mode success_and_current

        resp = admin_client.get(reverse('intention-list'), {"mode": "success_and_current"})
        assert resp.status_code == 200
        assert len(resp.json()['results']) == 4, "no platform filter"
        resp = admin_client.get(
            reverse('intention-list'), {'platform': cr.platform_id, "mode": "success_and_current"}
        )
        assert resp.status_code == 200
        assert len(resp.json()['results']) == 3, "with platform filter"

    @pytest.mark.parametrize(
        ['order_by'], (('start_date',), ('end_date',), ('timestamp',), ('error_code',))
    )
    @pytest.mark.parametrize(['desc'], ((True,), (False,), (None,)))
    def test_list_sorting(self, admin_client, order_by, desc):
        cr = CredentialsFactory()
        FetchIntentionFactory.create_batch(30, credentials=cr, attempt__credentials=cr)
        params = {'order_by': order_by}
        if desc is not None:
            params['desc'] = 'true' if desc else 'false'
        resp = admin_client.get(reverse('intention-list'), params)
        assert resp.status_code == 200
        records = resp.json()['results']
        assert len(records) == 30
        if order_by in ["timestamp", "error_code"]:
            values = [x['attempt'][order_by] for x in records]
        else:
            values = [x[order_by] for x in records]
        assert values == list(sorted(values, reverse=bool(desc)))

    @pytest.mark.parametrize(
        ['order_by', 'path'],
        (
            ('counter_report__code', ['counter_report_verbose', 'code']),
            ('credentials__platform__short_name', ['platform', 'short_name']),
            ('credentials__organization__short_name', ['organization', 'short_name']),
        ),
    )
    @pytest.mark.parametrize(['desc'], ((True,), (False,), (None,)))
    def test_list_sorting_nested_values(self, admin_client, order_by, path, desc):
        cr = CredentialsFactory()
        FetchIntentionFactory.create_batch(30, credentials=cr, attempt__credentials=cr)
        params = {'order_by': order_by}
        if desc is not None:
            params['desc'] = 'true' if desc else 'false'
        resp = admin_client.get(reverse('intention-list'), params)
        assert resp.status_code == 200
        records = resp.json()['results']
        assert len(records) == 30
        for part in path:
            records = [x[part] for x in records]
        assert records == list(sorted(records, reverse=bool(desc)))

    @pytest.mark.parametrize(['page_size'], ((5,), (10,), (25,)))
    def test_list_page_size(self, admin_client, page_size):
        cr = CredentialsFactory()
        FetchIntentionFactory.create_batch(30, credentials=cr, attempt__credentials=cr)
        resp = admin_client.get(reverse('intention-list'), {'page_size': page_size})
        assert resp.status_code == 200
        assert len(resp.json()['results']) == page_size

    def test_list_attempts_only(self, admin_client):
        cr = CredentialsFactory()
        FetchIntentionFactory.create_batch(23, credentials=cr, attempt__credentials=cr)
        FetchIntentionFactory.create_batch(19, credentials=cr, attempt=None)
        resp = admin_client.get(reverse('intention-list'), {'attempt': '1', 'mode': 'all'})
        assert resp.status_code == 200
        assert len(resp.json()['results']) == 23
        resp = admin_client.get(reverse('intention-list'), {'attempt': '0', 'mode': 'all'})
        assert resp.status_code == 200
        assert len(resp.json()['results']) == 19

    def test_list_filter_by_credentials(self, admin_client):
        cr1 = CredentialsFactory()
        cr2 = CredentialsFactory()
        FetchIntentionFactory.create_batch(29, credentials=cr1)
        FetchIntentionFactory.create_batch(31, credentials=cr2)
        resp = admin_client.get(reverse('intention-list'), {'credentials': cr1.pk})
        assert resp.status_code == 200
        assert len(resp.json()['results']) == 29
        resp = admin_client.get(reverse('intention-list'), {'credentials': cr2.pk})
        assert resp.status_code == 200
        assert len(resp.json()['results']) == 31


@pytest.mark.django_db(transaction=True)
class TestIntentionDeleteView:
    @pytest.mark.clickhouse
    @pytest.mark.usefixtures('clickhouse_on_off')
    @pytest.mark.parametrize(
        ['user', 'status_code'],
        [
            ['unauthenticated', 401],
            ['invalid', 401],
            ['user1', 403],
            ['user2', 403],
            ['admin1', 200],
            ['admin2', 403],
            ['master_admin', 200],
            ['master_user', 403],
            ['su', 200],
        ],
    )
    def test_intention_delete_view(self, basic1, clients, user, status_code, settings):
        cr1 = CredentialsFactory()
        cr2 = CredentialsFactory()
        fi1 = FetchIntentionFactory.create(credentials=cr1, start_date=date(2021, 1, 1))
        fi2 = FetchIntentionFactory.create(credentials=cr2, start_date=date(2021, 5, 1))
        ib1 = ImportBatchFullFactory.create(date=date(2021, 1, 1))
        fi1.attempt.import_batch = ib1
        fi1.attempt.save()

        if user == 'admin1':
            # admin1 is not admin of cr1.organization by default, so we make him
            UserOrganization.objects.get_or_create(
                user=basic1['users']['admin1'], organization=cr1.organization, is_admin=True
            )

        assert FetchIntention.objects.count() == 2
        assert SushiFetchAttempt.objects.count() == 2
        assert ImportBatch.objects.count() == 1
        # check that clickhouse integration works as expected
        if settings.CLICKHOUSE_SYNC_ACTIVE:
            assert (
                ch_backend.get_one_record(
                    AccessLogCube.query()
                    .filter(import_batch_id=ib1.pk)
                    .aggregate(sum=HSum('value'))
                ).sum
                == AccessLog.objects.aggregate(sum=Sum('value'))['sum']
            )

        resp = clients[user].post(
            reverse('intention-purge'),
            json.dumps(
                [
                    {
                        'credentials': cr1.pk,
                        'start_date': '2021-01-01',
                        'counter_report': fi1.counter_report_id,
                    }
                ]
            ),
            content_type='application/json',
        )
        assert resp.status_code == status_code
        if status_code == 200:
            assert FetchIntention.objects.count() == 1
            assert FetchIntention.objects.get().pk == fi2.pk, 'intention fi2 should remain'
            assert SushiFetchAttempt.objects.count() == 1, 'only one attempt should remain'
            assert ImportBatch.objects.count() == 0, 'import batch is deleted'
            assert AccessLog.objects.count() == 0, 'no access logs remain'
            assert resp.json() == {
                'logs.AccessLog': 20,
                'logs.ImportBatch': 1,
                'sushi.SushiFetchAttempt': 1,
                'scheduler.FetchIntention': 1,
            }, 'delete counts should match expectations'
            if settings.CLICKHOUSE_SYNC_ACTIVE:
                assert (
                    ch_backend.get_one_record(
                        AccessLogCube.query()
                        .filter(import_batch_id=ib1.pk)
                        .aggregate(sum=HSum('value'))
                    ).sum
                    == 0
                )
        else:
            assert FetchIntention.objects.count() == 2, 'the number of intentions is the same'
            assert SushiFetchAttempt.objects.count() == 2, 'number of attempts remains the same'
            assert ImportBatch.objects.count() == 1, 'no change in number of import batches'
            assert AccessLog.objects.count() == 20, 'no change in number of access logs'
            if settings.CLICKHOUSE_SYNC_ACTIVE:
                assert (
                    ch_backend.get_one_record(
                        AccessLogCube.query()
                        .filter(import_batch_id=ib1.pk)
                        .aggregate(HSum('value'))
                    ).sum
                    == AccessLog.objects.aggregate(sum=Sum('value'))['sum']
                )
