import pytest
import json

from django.urls import reverse

from scheduler import tasks
from scheduler.models import Automatic, FetchIntention
from sushi.models import BrokenCredentialsMixin as BS, CounterReportsToCredentials

from test_fixtures.scenarios.basic import (
    basic1,
    clients,
    data_sources,
    harvests,
    identities,
    organizations,
    platforms,
    users,
    counter_report_types,
    report_types,
    credentials,
    schedulers,
)
from test_fixtures.entities.fetchattempts import FetchAttemptFactory


@pytest.mark.django_db
class TestHarvestAPI:
    def test_list(self, basic1, clients, harvests):
        url = reverse('harvest-list')
        resp = clients["master"].get(url, {})
        assert resp.status_code == 200
        data = resp.json()["results"]
        assert len(data) == 2
        assert len(data[0]["intentions"]) == 2
        assert data[0]["stats"] == {"total": 2, "planned": 1}
        assert len(data[1]["intentions"]) == 3
        assert data[1]["stats"] == {"total": 3, "planned": 2}
        assert data[0]["pk"] > data[1]["pk"], "highest harvest pk first"

    def test_get(self, basic1, clients, harvests):
        url = reverse('harvest-detail', args=(harvests["anonymous"].pk,))
        resp = clients["master"].get(url, {})
        assert resp.status_code == 200
        data = resp.json()
        assert data["stats"] == {"total": 3, "planned": 2}
        assert len(data["intentions"]) == 3

        url = reverse('harvest-detail', args=(harvests["user1"].pk,))
        resp = clients["master"].get(url, {})
        assert resp.status_code == 200
        data = resp.json()
        assert data["stats"] == {"total": 2, "planned": 1}
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

        resp = clients["master"].post(
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
        assert data["stats"] == {"total": 2, "planned": 2}
        assert len(data["intentions"]) == 2
        assert data["last_updated_by"] == users["master"].pk
        assert stored_intentions_count + 2 == FetchIntention.objects.count()
        assert FetchIntention.objects.order_by('-pk')[0].priority >= FetchIntention.PRIORITY_NOW
        assert FetchIntention.objects.order_by('-pk')[1].priority >= FetchIntention.PRIORITY_NOW

        assert planned_urls == {
            credentials["standalone_tr"].url,
            credentials["standalone_br1_jr1"].url,
        }

    @pytest.mark.parametrize("user,length", (("master", 2), ("user1", 1), ("user2", 0),))
    def test_list_filtering(self, basic1, harvests, clients, user, length):
        url = reverse('harvest-list')
        resp = clients[user].get(url, {})
        assert resp.status_code == 200
        data = resp.json()["results"]
        assert len(data) == length

    @pytest.mark.parametrize(
        "user,anonymous_status,user1_status",
        (("master", 200, 200), ("user1", 404, 200), ("user2", 404, 404),),
    )
    def test_get_permissions(self, basic1, harvests, clients, user, anonymous_status, user1_status):
        url = reverse('harvest-detail', args=(harvests["anonymous"].pk,))
        resp = clients[user].get(url, {})
        assert resp.status_code == anonymous_status

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
        resp = clients["master"].post(
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
        resp = clients["master"].post(
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
        resp = clients["master"].post(
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
        resp = clients["master"].post(
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
        self, basic1, clients, credentials,
    ):

        url = reverse('harvest-list')
        resp = clients["master"].get(url, {})
        assert resp.status_code == 200
        data = resp.json()["results"]
        assert len(data) == 0

        # this should create automatic harvests
        Automatic.update_for_next_month()

        url = reverse('harvest-list')
        resp = clients["master"].get(url, {})
        assert resp.status_code == 200
        data = resp.json()["results"]
        assert len(data) == 2
        assert isinstance(data[0]['automatic'], int)
        assert isinstance(data[1]['automatic'], int)

        # check whether atomic is are present in details
        url = reverse('harvest-detail', args=(data[0]['pk'],))
        resp = clients["master"].get(url, {})
        assert resp.status_code == 200
        data = resp.json()
        assert data["automatic"] is not None
        assert 'month' in data["automatic"]
        assert 'organization' in data["automatic"]
        assert 'pk' in data['automatic']['organization']
        assert 'name' in data['automatic']['organization']
        assert 'short_name' in data['automatic']['organization']


@pytest.mark.django_db()
class TestFetchIntentionAPI:
    def test_list(self, basic1, clients, harvests):

        url = reverse('harvest-intention-list', args=(harvests["anonymous"].pk,))
        resp = clients["master"].get(url, {})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3

        url = reverse('harvest-intention-list', args=(harvests["user1"].pk,))
        resp = clients["master"].get(url, {})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    @pytest.mark.parametrize(
        "user,anonymous_status,user1_status",
        (("master", 200, 200), ("user1", 404, 200), ("user2", 404, 404),),
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
        resp = clients["master"].get(url, {})
        assert resp.status_code == 200

        url = reverse(
            'harvest-intention-detail',
            args=(harvests["user1"].pk, harvests["anonymous"].latest_intentions.first().pk),
        )

        resp = clients["master"].get(url, {})
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
        resp = clients["master"].get(url, {})
        assert resp.status_code == 200
        # create new intention by setting .pk to None and saving
        old_pk = resp.json()['pk']
        intention = FetchIntention.objects.get(pk=old_pk)
        intention.retry_id = intention.pk
        intention.pk = None
        intention.data_not_ready_retry = 1
        intention.attempt = None
        intention.save()

        # try to get old and new intentions via get
        resp = clients['master'].get(
            reverse('harvest-intention-detail', args=(harvests['anonymous'].pk, intention.pk),)
        )
        assert resp.status_code == 200, 'new intention should be reachable'
        resp = clients['master'].get(
            reverse('harvest-intention-detail', args=(harvests['anonymous'].pk, old_pk),)
        )
        assert resp.status_code == 200, 'old intention should be reachable as well'

        # try to get old and new intentions via list
        resp = clients['master'].get(
            reverse('harvest-intention-list', args=(harvests['anonymous'].pk,),)
        )
        assert resp.status_code == 200
        assert old_pk not in [e["pk"] for e in resp.json()], 'by default old should be hidden'

        resp = clients['master'].get(
            reverse('harvest-intention-list', args=(harvests['anonymous'].pk,),) + '?list_all=1'
        )
        assert resp.status_code == 200
        assert old_pk in [e["pk"] for e in resp.json()], '"list_all" param will show all'

    @pytest.mark.parametrize(
        "user,anonymous_status,user1_status",
        (("master", 200, 200), ("user1", 404, 200), ("user2", 404, 404),),
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
