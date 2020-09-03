from copy import deepcopy

import pytest

from core.tests.test_sync import data_source
from organizations.logic.sync import OrganizationSyncer
from organizations.models import Organization


@pytest.mark.django_db
class TestLogicSync:

    src_data = [
        {
            'class': 'Organization',
            'id': 123,
            'refs': {'type': [603]},
            'vals': {
                'address of residence': [
                    {
                        'country': 'Czech Republic',
                        'postcode': '110 00',
                        'street': 'Štěpánská 123',
                        'town': 'Praha 1',
                    }
                ],
                'ico': [123456789],
                'name@cs': ['Whatever Praha s.r.o.'],
                'short name@cs': ['Whatever'],
                'url': ['http://www.testtesttest.cz/'],
            },
        },
        {
            'class': 'Organization',
            'id': 234,
            'refs': {},
            'vals': {
                'address of residence': [
                    {
                        'country': 'ČR',
                        'postcode': '61300',
                        'street': 'Zemědělská 156',
                        'town': 'Brno',
                    }
                ],
                'czechelib id': ['TEST-AABBBRNO'],
                'fte': [120],
                'ico': [23456664],
                'name@cs': ['Testovací univerzita v Brně'],
                'name@en': ['Test University Brno'],
                'short name@cs': ['TestBr'],
                'url': ['http://testbrno.cz'],
            },
        },
    ]

    trans_data = [
        {
            'ext_id': 123,
            'address': {
                'country': 'Czech Republic',
                'postcode': '110 00',
                'street': 'Štěpánská 123',
                'town': 'Praha 1',
            },
            'ico': 123456789,
            'name_cs': 'Whatever Praha s.r.o.',
            'short_name_cs': 'Whatever',
            'url': 'http://www.testtesttest.cz/',
        },
        {
            'ext_id': 234,
            'address': {
                'country': 'ČR',
                'postcode': '61300',
                'street': 'Zemědělská 156',
                'town': 'Brno',
            },
            'internal_id': 'TEST-AABBBRNO',
            'fte': 120,
            'ico': 23456664,
            'name_cs': 'Testovací univerzita v Brně',
            'name_en': 'Test University Brno',
            'short_name_cs': 'TestBr',
            'url': 'http://testbrno.cz',
        },
    ]

    def test_fixture_works(self, organizations):
        assert len(organizations) == Organization.objects.count()

    def test_random_fixture_works(self, organizations_random):
        assert len(organizations_random) == Organization.objects.count()

    def test_organization_sync_translation(self, data_source):
        syncer = OrganizationSyncer(data_source)
        for rec_in, rec_out in zip(self.src_data, self.trans_data):
            tr_rec = syncer.translate_record(rec_in)
            assert tr_rec == rec_out

    def test_organization_sync_sync(self, data_source):
        syncer = OrganizationSyncer(data_source)
        assert Organization.objects.count() == 0
        stats = syncer.sync_data(self.src_data)
        assert Organization.objects.count() == 2
        assert stats[syncer.Status.NEW] == 2
        assert stats[syncer.Status.UNCHANGED] == 0
        assert stats[syncer.Status.SYNCED] == 0

    def test_organization_sync_resync(self, data_source):
        syncer = OrganizationSyncer(data_source)
        assert Organization.objects.count() == 0
        stats = syncer.sync_data(self.src_data)
        assert Organization.objects.count() == 2
        assert stats[syncer.Status.NEW] == 2
        assert stats[syncer.Status.UNCHANGED] == 0
        assert stats[syncer.Status.SYNCED] == 0
        # resync
        stats = syncer.sync_data(self.src_data)
        assert Organization.objects.count() == 2
        assert stats[syncer.Status.NEW] == 0
        assert stats[syncer.Status.UNCHANGED] == 2

    def test_organization_sync_resync_with_change(self, data_source):
        syncer = OrganizationSyncer(data_source)
        assert Organization.objects.count() == 0
        stats = syncer.sync_data(self.src_data)
        assert Organization.objects.count() == 2
        assert stats[syncer.Status.NEW] == 2
        assert stats[syncer.Status.UNCHANGED] == 0
        assert stats[syncer.Status.SYNCED] == 0
        # resync
        # the following line will not cause change - we do not detect missing values
        src_data = deepcopy(self.src_data)
        src_data[0]['vals']['ico'] = 987
        del src_data[1]['vals']['ico']
        stats = syncer.sync_data(src_data)
        assert Organization.objects.count() == 2
        assert stats[syncer.Status.NEW] == 0
        assert stats[syncer.Status.UNCHANGED] == 1
        assert stats[syncer.Status.SYNCED] == 1

    def test_organization_sync_with_parental_links(self, data_source):
        syncer = OrganizationSyncer(data_source)
        assert Organization.objects.count() == 0
        src_data = deepcopy(self.src_data)
        src_data[1]['refs']['controlled by'] = [src_data[0]['id']]  # add first as parent to second
        syncer.sync_data(src_data)
        assert Organization.objects.count() == 2
        org0 = Organization.objects.get(ext_id=src_data[0]['id'])
        org1 = Organization.objects.get(ext_id=src_data[1]['id'])
        assert org1.parent == org0
