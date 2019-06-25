from pprint import pprint

import pytest

from organizations.logic.sync import OrganizationSyncer
from organizations.models import Organization
from .fixtures import organizations, organizations_random


@pytest.mark.django_db
class TestLogicSync(object):

    src_data = [
        {'class': 'Organization',
         'id': 123,
         'refs': {'type': [603]},
         'vals': {'address of residence': [{'country': 'Czech Republic',
                                            'postcode': '110 00',
                                            'street': 'Štěpánská 123',
                                            'town': 'Praha 1'}],
                  'ico': [123456789],
                  'name@cs': ['Whatever Praha s.r.o.'],
                  'short name@cs': ['Whatever'],
                  'url': ['http://www.testtesttest.cz/']}
         },
        {'class': 'Organization',
         'id': 234,
         'refs': {},
         'vals': {'address of residence': [{'country': 'ČR',
                                            'postcode': '61300',
                                            'street': 'Zemědělská 156',
                                            'town': 'Brno'}],
                  'czechelib id': ['TEST-AABBBRNO'],
                  'fte': [120],
                  'ico': [23456664],
                  'name@cs': ['Testovací univerzita v Brně'],
                  'name@en': ['Test University Brno'],
                  'short name@cs': ['TestBr'],
                  'url': ['http://testbrno.cz']}
         },
    ]

    trans_data = [
        {'ext_id': 123,
         'address': {'country': 'Czech Republic',
                     'postcode': '110 00',
                     'street': 'Štěpánská 123',
                     'town': 'Praha 1'},
         'ico': 123456789,
         'name_cs': 'Whatever Praha s.r.o.',
         'short_name_cs': 'Whatever',
         'url': 'http://www.testtesttest.cz/',
         },
        {'ext_id': 234,
         'address': {'country': 'ČR',
                     'postcode': '61300',
                     'street': 'Zemědělská 156',
                     'town': 'Brno'},
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

    def test_organization_sync_translation(self):
        syncer = OrganizationSyncer()
        for rec_in, rec_out in zip(self.src_data, self.trans_data):
            tr_rec = syncer.translate_record(rec_in)
            pprint(tr_rec)
            assert tr_rec == rec_out

    def test_organization_sync_sync(self):
        syncer = OrganizationSyncer()
        assert Organization.objects.count() == 0
        stats = syncer.sync_data(self.src_data)
        assert Organization.objects.count() == 2
        assert stats[syncer.Status.NEW] == 2
        assert stats[syncer.Status.UNCHANGED] == 0
        assert stats[syncer.Status.SYNCED] == 0

    def test_organization_sync_resync(self):
        syncer = OrganizationSyncer()
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

    def test_organization_sync_resync_with_change(self):
        syncer = OrganizationSyncer()
        assert Organization.objects.count() == 0
        stats = syncer.sync_data(self.src_data)
        assert Organization.objects.count() == 2
        assert stats[syncer.Status.NEW] == 2
        assert stats[syncer.Status.UNCHANGED] == 0
        assert stats[syncer.Status.SYNCED] == 0
        # resync
        # the following line will not cause change - we do not detect missing values
        self.src_data[0]['vals']['ico'] = 987
        del self.src_data[1]['vals']['ico']
        stats = syncer.sync_data(self.src_data)
        assert Organization.objects.count() == 2
        assert stats[syncer.Status.NEW] == 0
        assert stats[syncer.Status.UNCHANGED] == 1
        assert stats[syncer.Status.SYNCED] == 1
