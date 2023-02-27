import codecs
from csv import DictReader
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from django.urls import reverse
from publications.logic.fake_data import (
    PlatformTitleFactory,
    TitleFactory,
    TitleOverlapBatchFactory,
)
from publications.logic.title_list_overlap import CsvTitleListOverlapReader
from publications.models import TitleOverlapBatch, TitleOverlapBatchState
from publications.tasks import process_title_overlap_batch_task
from publications.tests.test_api import MockTask

from test_fixtures.entities.organizations import OrganizationFactory
from test_fixtures.entities.platforms import PlatformFactory
from test_fixtures.scenarios.basic import (  # noqa - fixtures
    basic1,
    clients,
    data_sources,
    identities,
    organizations,
    platforms,
    users,
)


@pytest.mark.django_db
class TestTitleListOverlap:
    @pytest.mark.parametrize(
        ['batch_size', 'num_queries'], [(1, 6), (2, 3), (6, 1), (10, 1), (1000, 1)]
    )
    @pytest.mark.parametrize(
        ['merge_issns', 'expected_counts'],
        [(False, [1, 1, 0, 0, 0, 0]), (True, [1, 1, 0, 0, 1, 0])],
    )
    def test_title_matching(
        self, merge_issns, expected_counts, batch_size, num_queries, django_assert_max_num_queries
    ):
        p_foo = PlatformFactory.create(name='Foo')
        p_bar = PlatformFactory.create(name='Bar')
        # t1 is on platform Foo only
        t1 = TitleFactory.create(isbn='9780787960186')
        PlatformTitleFactory.create(title=t1, platform=p_foo)
        # t2 is on both platforms
        t2 = TitleFactory.create(issn='1234-5678')
        PlatformTitleFactory.create(title=t2, platform=p_foo)
        PlatformTitleFactory.create(title=t2, platform=p_bar)

        reader = CsvTitleListOverlapReader()
        dump = BytesIO()
        with open('test-data/tagging_batch/plain-title-list.csv', 'r') as infile:
            with django_assert_max_num_queries(num_queries * 2):  # 2 queries per batch
                data = list(
                    reader.process_source(
                        infile, merge_issns=merge_issns, batch_size=batch_size, dump_file=dump
                    )
                )
        assert len(data) == 6
        assert [len(rec.title_ids) for rec in data] == expected_counts
        # check the dump file
        dump.seek(0)
        dump_reader = DictReader(codecs.getreader('utf-8')(dump))
        reader_recs = list(dump_reader)
        assert dump_reader.fieldnames == [
            'Name',
            'ISBN',
            'issn',
            'eISSN',
            'note',
            '_Found on platforms_',
            '_Matched titles_',
        ]
        for i, rec in enumerate(reader_recs):
            if expected_counts[i] == 0:
                assert rec['_Matched titles_'] == ''
                assert rec['_Found on platforms_'] == ''
            else:
                assert rec['_Matched titles_'] != ''
                if int(rec['_Matched titles_']) == t1.pk:
                    assert rec['_Found on platforms_'] == 'Foo'
                else:
                    assert rec['_Found on platforms_'] == 'Bar, Foo'

    @pytest.mark.parametrize(
        [
            't1_pfoo_org',
            't2_pfoo_org',
            't2_pbar_org',
            'query_org',
            't1_pfoo_match',
            't2_pfoo_match',
            't2_pbar_match',
        ],
        [
            (0, 0, 0, 0, True, True, True),  # the same org for all title-platforms and the query
            (0, 1, 1, 0, True, False, False),  # t2 not matched because of different org
            (0, 1, 1, 1, False, True, True),  # t1 not matched because of different org
            (0, 0, 1, 0, True, True, False),  # t2 only matched on Foo
        ],
    )
    def test_title_matching_organizations(
        self,
        t1_pfoo_org,
        t2_pfoo_org,
        t2_pbar_org,
        query_org,
        t1_pfoo_match,
        t2_pfoo_match,
        t2_pbar_match,
    ):
        orgs = OrganizationFactory.create_batch(2)
        p_foo = PlatformFactory.create(name='Foo')
        p_bar = PlatformFactory.create(name='Bar')
        # t1 is on platform Foo only
        t1 = TitleFactory.create(isbn='9780787960186')
        PlatformTitleFactory.create(title=t1, platform=p_foo, organization=orgs[t1_pfoo_org])
        # t2 is on both platforms
        t2 = TitleFactory.create(issn='1234-5678')
        PlatformTitleFactory.create(title=t2, platform=p_foo, organization=orgs[t2_pfoo_org])
        PlatformTitleFactory.create(title=t2, platform=p_bar, organization=orgs[t2_pbar_org])

        reader = CsvTitleListOverlapReader(organization=orgs[query_org])
        dump = BytesIO()
        input_data = StringIO("Name,ISBN,issn\nFoo,9780787960186,\nBar,,1234-5678\n")
        data = list(reader.process_source(input_data, dump_file=dump))
        assert len(data) == 2
        # check the dump file
        dump.seek(0)
        dump_reader = DictReader(codecs.getreader('utf-8')(dump))
        t1_rec, t2_rec = list(dump_reader)
        if t1_pfoo_match:
            assert 'Foo' in t1_rec['_Found on platforms_']
        else:
            assert 'Foo' not in t1_rec['_Found on platforms_']
        if t2_pfoo_match:
            assert 'Foo' in t2_rec['_Found on platforms_']
        else:
            assert 'Foo' not in t2_rec['_Found on platforms_']
        if t2_pbar_match:
            assert 'Bar' in t2_rec['_Found on platforms_']
        else:
            assert 'Bar' not in t2_rec['_Found on platforms_']


plain_test_file = Path(__file__).parent / '../../../test-data/tagging_batch/plain-title-list.csv'


@pytest.mark.django_db
class TestTitleOverlapBatchModel:
    def test_title_overlap_batch_no_titles(self, inmemory_media):
        batch = TitleOverlapBatchFactory.create(source_file=plain_test_file)
        assert batch.state == TitleOverlapBatchState.INITIAL
        batch.process()
        assert batch.state == TitleOverlapBatchState.DONE
        assert 'stats' in batch.processing_info
        assert batch.processing_info['stats']['row_count'] == 6
        assert batch.processing_info['stats']['no_match'] == 6
        assert batch.processing_info['stats']['unique_matched_titles'] == 0
        assert batch.processing_info['recognized_columns'] == ['eISSN', 'ISBN', 'issn', 'Name']
        assert batch.annotated_file.name.endswith('-annotated.csv')
        reader = DictReader(codecs.getreader('utf-8')(batch.annotated_file))
        assert '_Matched titles_' in reader.fieldnames
        assert '_Found on platforms_' in reader.fieldnames

    @pytest.mark.parametrize(
        ['used_org', 'matched_rows', 'matched_titles'], [(0, 3, 2), (1, 0, 0), (-1, 3, 2)]
    )
    def test_title_overlap_batch_with_titles(
        self, inmemory_media, used_org, matched_rows, matched_titles
    ):
        # two organizations
        orgs = OrganizationFactory.create_batch(2)
        # two titles - both connected to the first organization
        t1 = TitleFactory.create(isbn='9780787960186')
        PlatformTitleFactory.create(title=t1, organization=orgs[0])
        t2 = TitleFactory.create(issn='1234-5678')
        PlatformTitleFactory.create(title=t2, organization=orgs[0])
        # create the batch
        org = orgs[used_org] if used_org >= 0 else None
        batch = TitleOverlapBatchFactory.create(source_file=plain_test_file, organization=org)
        assert batch.state == TitleOverlapBatchState.INITIAL
        batch.process()
        assert batch.state == TitleOverlapBatchState.DONE
        assert batch.processing_info['stats']['row_count'] == 6
        assert batch.processing_info['stats']['no_match'] == 6 - matched_rows
        assert batch.processing_info['stats']['unique_matched_titles'] == matched_titles


@pytest.mark.django_db
class TestTitleOverlapBatchAPI:
    @pytest.mark.parametrize(('user_type', 'expected_count'), [('admin1', 1), ('user1', 0)])
    def test_title_overlap_batch_list(self, clients, users, user_type, expected_count):
        """
        Check that each user can only see his own batches.
        """
        TitleOverlapBatchFactory.create(last_updated_by=users['admin1'])
        response = clients[user_type].get(reverse('title-overlap-batch-list'))
        assert response.status_code == 200
        assert len(response.data) == expected_count

    @pytest.mark.parametrize(
        ('user_type', 'can_create_with_standalone_org', 'can_create_no_org'),
        [
            ('unauthenticated', None, None),
            ('invalid', None, None),
            ('user1', False, False),
            ('user2', True, False),  # belongs to standalone org
            ('master_admin', True, True),  # is consortium admin
            ('master_user', True, True),  # is consortium read-only user
            ('admin1', False, False),
            ('admin2', True, False),  # is admin of standalone org
            ('su', True, True),  # is superuser
        ],
    )
    @pytest.mark.parametrize('assign_org', [True, False])
    def test_create_batch_permissions(
        self,
        clients,
        organizations,
        basic1,
        inmemory_media,
        user_type,
        can_create_with_standalone_org,
        can_create_no_org,
        assign_org,
    ):
        """
        Test that user can only assign organization to which he belongs to the batch.
        """
        # create the batch
        org = organizations['standalone'] if assign_org else None
        with open(plain_test_file, 'rb') as f:
            # we need to mock the task so that it is not executed in the test environment
            response = clients[user_type].post(
                reverse('title-overlap-batch-list'),
                data={'source_file': f, 'organization': org.pk if org else ''},
                format='multipart',
            )
        success = can_create_with_standalone_org if assign_org else can_create_no_org
        if success is None:
            # user is not authenticated
            assert response.status_code == 401
        elif success:
            assert response.status_code == 201
            if assign_org:
                assert TitleOverlapBatch.objects.get(pk=response.data['pk']).organization == org
            else:
                assert TitleOverlapBatch.objects.get(pk=response.data['pk']).organization is None
        else:
            assert response.status_code == 403

    def test_create_batch(self, admin_client, inmemory_media):
        """
        Check the workflow of creating a batch and the structure of the serialized data.
        """
        # create the batch
        with open(plain_test_file, 'rb') as f, patch(
            'publications.views.process_title_overlap_batch_task'
        ) as mock:
            response = admin_client.post(
                reverse('title-overlap-batch-list'), data={'source_file': f}, format='multipart'
            )
            assert not mock.delay.called
        assert response.status_code == 201
        batch = TitleOverlapBatch.objects.get(pk=response.data['pk'])
        assert batch.state == TitleOverlapBatchState.INITIAL
        # check the serialized data
        assert type(response.data['pk']) is int
        assert type(response.data['state']) is str
        assert type(response.data['organization']) is int or response.data['organization'] is None
        assert type(response.data['source_file']) is str
        assert response.data['source_file'].endswith('.csv')
        assert response.data['annotated_file'] is None
        assert type(response.data['processing_info']) is dict
        # perform the processing task synchronously
        batch.state = TitleOverlapBatchState.PROCESSING
        batch.save()
        process_title_overlap_batch_task(batch.pk)
        # check the batch data
        response = admin_client.get(reverse('title-overlap-batch-detail', args=[batch.pk]))
        assert response.status_code == 200
        assert response.data['state'] == TitleOverlapBatchState.DONE
        assert response.data['annotated_file'].endswith('-annotated.csv')

    def test_process_batch(self, admin_client, inmemory_media):
        """
        Check the endpoint for processing a batch in the context of the workflow of creating a batch
        and then processing it.
        """
        # create the batch
        with open(plain_test_file, 'rb') as f:
            response = admin_client.post(
                reverse('title-overlap-batch-list'), data={'source_file': f}, format='multipart'
            )
        assert response.status_code == 201
        batch = TitleOverlapBatch.objects.get(pk=response.data['pk'])
        assert batch.state == TitleOverlapBatchState.INITIAL
        # call the process endpoint
        with patch('publications.views.process_title_overlap_batch_task') as mock:
            mock.delay.return_value = MockTask()
            response = admin_client.post(reverse('title-overlap-batch-process', args=[batch.pk]))
            assert response.status_code == 202
            assert response.data['batch']['state'] == TitleOverlapBatchState.PROCESSING
            assert 'task_id' in response.data
            assert mock.delay.called
        # simulate the processing task synchronously
        process_title_overlap_batch_task(batch.pk)
        # check the batch data
        response = admin_client.get(reverse('title-overlap-batch-detail', args=[batch.pk]))
        assert response.status_code == 200
        assert response.data['state'] == TitleOverlapBatchState.DONE
        assert response.data['annotated_file'].endswith('-annotated.csv')

    @pytest.mark.parametrize(('user_type', 'can_delete'), [('admin1', True), ('user1', False)])
    def test_title_overlap_batch_delete(self, clients, users, user_type, can_delete):
        """
        Check that each user can only see his own batches.
        """
        batch = TitleOverlapBatchFactory.create(last_updated_by=users['admin1'])
        response = clients[user_type].delete(reverse('title-overlap-batch-detail', args=[batch.pk]))
        if can_delete:
            assert response.status_code == 204
        else:
            assert response.status_code == 404
