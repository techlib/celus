import codecs
import csv
from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.files.base import ContentFile
from rest_framework.reverse import reverse

from publications.tests.test_api import MockTask
from tags.logic.fake_data import TagForTitleFactory, TaggingBatchFactory, TagClassFactory
from tags.models import TaggingBatch, TaggingBatchState, TagScope
from tags.tasks import (
    tagging_batch_assign_tag_task,
    tagging_batch_preflight_task,
    tagging_batch_unassign_task,
)
from test_fixtures.entities.titles import TitleFactory
from test_fixtures.scenarios.basic import (  # noqa - fixtures
    basic1,
    clients,
    data_sources,
    identities,
    organizations,
    platforms,
    users,
)

plain_test_file = Path(__file__).parent / '../../../test-data/tagging_batch/plain-title-list.csv'


@pytest.mark.django_db
class TestBatchTagging:
    def test_tagging_batch_preflight(self, inmemory_media):
        TitleFactory.create(isbn='9780787960186')
        TitleFactory.create(issn='1234-5678')
        tb = TaggingBatchFactory.create(source_file=plain_test_file)
        tb.do_preflight()
        assert tb.preflight != {}
        assert tb.preflight['stats'] == {'row_count': 6, 'no_match': 3, 'unique_matched_titles': 2}
        assert tb.preflight['explicit_tags'] is False
        assert tb.preflight['recognized_columns'] == ['eISSN', 'ISBN', 'issn', 'Name']

    @pytest.mark.parametrize(
        ['create_missing_titles', 'title_count'],
        [
            (True, 5),  # 2 are matched by 3 lines; 3 lines create new titles => 5
            (False, 2),  # 2 are matched by 3 lines => 2
        ],
    )
    def test_tagging_batch_tagging(self, inmemory_media, users, create_missing_titles, title_count):
        TitleFactory.create(isbn='9780787960186')
        TitleFactory.create(issn='1234-5678')
        tb = TaggingBatchFactory.create(
            source_file=plain_test_file, last_updated_by=users['admin1']
        )
        tb.do_preflight()
        tag = TagForTitleFactory.create()
        tb.tag = tag
        tb.state = TaggingBatchState.IMPORTING
        tb.assign_tag(create_missing_titles=create_missing_titles)
        assert tb.state == TaggingBatchState.IMPORTED
        assert tb.postflight['stats']['tagged_titles'] == title_count
        assert tag.titles.count() == title_count

    def test_tagging_with_exclusive_tags(self, inmemory_media, users):
        t1 = TitleFactory.create(isbn='9780787960186')
        t2 = TitleFactory.create(issn='1234-5678')
        tc = TagClassFactory.create(exclusive=True, scope=TagScope.TITLE)
        tag1 = TagForTitleFactory.create(tag_class=tc)
        tag2 = TagForTitleFactory.create(tag_class=tc)
        tag1.tag(t1, users['admin1'])
        #
        tb = TaggingBatchFactory.build(
            source_file=plain_test_file,
            last_updated_by=users['admin1'],
            tag=tag2,
            state=TaggingBatchState.IMPORTING,
        )
        tb.save()
        tb.assign_tag()
        assert tb.state == TaggingBatchState.IMPORTED
        assert t1.tags.count() == 1, 't1 should have only the first tag'
        assert t1.tags.all()[0] == tag1, 't1 should have the first tag'
        assert t2.tags.count() == 1, 't2 should be tagged with the second tag'
        assert t2.tags.all()[0] == tag2, 't2 should have the second tag'
        assert tb.postflight['stats']['unique_matched_titles'] == 2
        assert tb.titletag_set.count() == 1, 'only one titletag'
        assert tb.postflight['stats']['tagged_titles'] == 1

    def test_batch_tagging_file_content(self, inmemory_media, users):
        """
        Test that an annotated_file is correctly created during preflight and processing
        """
        TitleFactory.create(isbn='9780787960186')
        TitleFactory.create(issn='1234-5678')
        tb = TaggingBatchFactory.create(
            source_file=plain_test_file, last_updated_by=users['admin1']
        )
        tb.do_preflight()
        assert tb.state == TaggingBatchState.PREFLIGHT
        stream = codecs.getreader('utf-8')(tb.annotated_file)
        reader = csv.DictReader(stream)
        assert '_Celus info_' in reader.fieldnames
        row1 = next(reader)
        assert row1['ISBN'] == '9780787960186'
        assert row1['_Celus info_'].startswith('1 match')

        # check that the annotated file is updated during import
        # first replace the file with empty one
        tb.annotated_file = ContentFile(b'', name=tb.annotated_file.name)
        tb.save()
        tag = TagForTitleFactory.create()
        tb.tag = tag
        tb.state = TaggingBatchState.IMPORTING
        tb.assign_tag(create_missing_titles=False)
        assert tb.state == TaggingBatchState.IMPORTED
        # recheck
        stream = codecs.getreader('utf-8')(tb.annotated_file)
        reader = csv.DictReader(stream)
        assert '_Celus info_' in reader.fieldnames
        row1 = next(reader)
        assert row1['ISBN'] == '9780787960186'
        assert row1['_Celus info_'].startswith('1 match')

    def test_tagging_batch_unassign(self, inmemory_media, users):
        TitleFactory.create(isbn='9780787960186')
        TitleFactory.create(issn='1234-5678')
        tb = TaggingBatchFactory.create(
            source_file=plain_test_file, last_updated_by=users['admin1']
        )
        tb.do_preflight()
        tag = TagForTitleFactory.create()
        tb.tag = tag
        tb.state = TaggingBatchState.IMPORTING
        tb.assign_tag()
        assert tag.titles.count() == 2, 'two titles are tagged'
        # manually tag some title
        extra = TitleFactory.create()
        tag.tag(extra, users['admin1'])
        assert tag.titles.count() == 3, 'three titles are tagged'
        # the un-assigning itself
        tb.state = TaggingBatchState.UNDOING
        tb.unassign_tag()
        assert tag.titles.count() == 1, 'only the one extra title is tagged'


@pytest.mark.django_db
class TestBatchTaggingAPI:
    @pytest.mark.parametrize(
        ['owner_type'],
        [
            ('user1',),
            ('user2',),
            ('admin1',),
            ('admin2',),
            ('master_admin',),
            ('master_user',),
            ('su',),
        ],
    )
    @pytest.mark.parametrize(
        ['client_type'],
        [
            ('user1',),
            ('user2',),
            ('admin1',),
            ('admin2',),
            ('master_admin',),
            ('master_user',),
            ('su',),
        ],
    )
    def test_tagging_batch_visibility(
        self, inmemory_media, clients, users, owner_type, client_type
    ):
        """
        Test that only owner can see tagging batch he created
        """
        tb = TaggingBatchFactory.create(
            source_file=plain_test_file, last_updated_by=users[owner_type]
        )
        # test the detail endpoint
        resp = clients[client_type].get(reverse('tagging-batch-detail', args=[tb.pk]))
        assert resp.status_code == (200 if owner_type == client_type else 404)
        # test the list endpoint
        resp = clients[client_type].get(reverse('tagging-batch-list'))
        assert resp.status_code == 200
        assert len(resp.json()) == (1 if owner_type == client_type else 0)

    def test_tagging_batch_file_upload(self, inmemory_media, clients, users):
        with plain_test_file.open('rb') as infile, patch(
            'tags.views.tagging_batch_preflight_task'
        ) as preflight_task:
            resp = clients['admin1'].post(reverse('tagging-batch-list'), {'source_file': infile})
            preflight_task.delay.assert_called(), 'preflight should be started on batch creation'
            preflight_task.delay.assert_called_with(resp.json()['pk'], 'http://testserver/')
        assert resp.status_code == 201
        tb = TaggingBatch.objects.get()
        assert resp.json()['pk'] == tb.pk
        assert tb.last_updated_by == users['admin1']

    @pytest.mark.parametrize(
        ['existing_tb', 'existing_tag', 'tb_state', 'status_code'],
        [
            (False, False, TaggingBatchState.PREFLIGHT, 404),
            (True, False, TaggingBatchState.PREFLIGHT, 400),
            (False, True, TaggingBatchState.PREFLIGHT, 404),
            (True, True, TaggingBatchState.INITIAL, 400),
            (True, True, TaggingBatchState.PREFAILED, 400),
            (True, True, TaggingBatchState.IMPORTED, 400),
            (True, True, TaggingBatchState.IMPORTING, 400),
            (True, True, TaggingBatchState.PREFLIGHT, 202),
        ],
    )
    def test_tagging_batch_tagging(
        self, inmemory_media, clients, users, existing_tb, existing_tag, tb_state, status_code
    ):
        # prepare the batch
        TitleFactory.create(isbn='9780787960186')
        TitleFactory.create(issn='1234-5678')
        tb = TaggingBatchFactory.create(
            source_file=plain_test_file, last_updated_by=users['admin1']
        )
        tag = TagForTitleFactory.create()
        if tb_state not in [TaggingBatchState.INITIAL, TaggingBatchState.PREFAILED]:
            tb.do_preflight()
        if tb_state in [TaggingBatchState.IMPORTING, TaggingBatchState.IMPORTED]:
            tb.tag = tag
        tb.state = tb_state
        tb.save()
        # apply a tag to all the titles
        with patch('tags.views.tagging_batch_assign_tag_task') as tagging_task:
            tagging_task.apply_async.return_value = MockTask()
            resp = clients['admin1'].post(
                reverse('tagging-batch-assign-tags', args=[tb.pk if existing_tb else tb.pk + 1]),
                {'tag': tag.pk if existing_tag else tag.pk + 1},
            )
            assert resp.status_code == status_code
            if status_code == 202:
                tagging_task.apply_async.assert_called(), 'the tagging task should be started'
                tb.refresh_from_db()
                assert tb.state == TaggingBatchState.IMPORTING

    def test_tagging_batch_tagging_no_tags_attr(self, inmemory_media, clients, users):
        tb = TaggingBatchFactory.create(
            source_file=plain_test_file, last_updated_by=users['admin1']
        )
        tb.do_preflight()
        resp = clients['admin1'].post(reverse('tagging-batch-assign-tags', args=[tb.pk]), {})
        assert resp.status_code == 400

    def test_tagging_batch_delete(self, inmemory_media, clients, users):
        TitleFactory.create(isbn='9780787960186')
        tag = TagForTitleFactory.create()
        # for some reason when running in several threads, the following fails on a
        # constraint failure - it seems the `tags` post-generation hook is not run
        # before the object is saved which leads to constraint failing
        # we side-step the issue by building and then saving
        tb = TaggingBatchFactory.build(
            source_file=plain_test_file,
            last_updated_by=users['admin1'],
            tag=tag,
            state=TaggingBatchState.IMPORTING,
        )
        tb.save()
        tb.assign_tag()
        assert tag.titles.count() > 0
        resp = clients['admin1'].delete(reverse('tagging-batch-detail', args=[tb.pk]))
        assert resp.status_code == 204
        assert TaggingBatch.objects.filter(pk=tb.pk).count() == 0, 'batch was deleted'
        assert tag.titles.count() > 0, 'the tag is still assigned to the titles'

    @pytest.mark.parametrize(
        ['user_type', 'can_delete'],
        [
            ('user1', False),
            ('user2', True),
            ('admin1', False),
            ('admin2', False),
            ('master_admin', False),
            ('master_user', False),
            ('su', False),
        ],
    )
    def test_tagging_batch_delete_access(
        self, inmemory_media, clients, users, user_type, can_delete
    ):
        """
        Test that only owner can delete a title list

        Note: this is covered by the visibility test above, but I keep it here in case
              we changed how that behaves, so that we do not forget to test the delete method
        """
        tb = TaggingBatchFactory.create(source_file=plain_test_file, last_updated_by=users['user2'])
        resp = clients[user_type].delete(reverse('tagging-batch-detail', args=[tb.pk]))
        if can_delete:
            assert resp.status_code == 204
            assert TaggingBatch.objects.filter(pk=tb.pk).count() == 0, 'batch was deleted'
        else:
            assert resp.status_code == 404
            assert TaggingBatch.objects.filter(pk=tb.pk).count() == 1, 'batch was not deleted'

    def test_tagging_batch_unassign(self, inmemory_media, clients, users):
        TitleFactory.create(isbn='9780787960186')
        tag = TagForTitleFactory.create()
        tb = TaggingBatchFactory.build(
            source_file=plain_test_file,
            last_updated_by=users['admin1'],
            tag=tag,
            state=TaggingBatchState.IMPORTING,
        )
        tb.save()
        tb.assign_tag()
        assert tag.titles.count() > 0
        with patch('tags.views.tagging_batch_unassign_task') as untagging_task:
            untagging_task.apply_async.return_value = MockTask()
            resp = clients['admin1'].post(reverse('tagging-batch-unassign', args=[tb.pk]))
            assert resp.status_code == 202
            untagging_task.apply_async.assert_called(), 'the un-tagging task should be started'


@pytest.mark.django_db
class TestTasks:
    @pytest.mark.parametrize(
        ['state', 'is_processed'],
        [(TaggingBatchState.INITIAL, True),]
        + [
            (state, False)
            for state in TaggingBatchState.values
            if state != TaggingBatchState.INITIAL
        ],
    )
    def test_tagging_batch_preflight_task(self, inmemory_media, users, state, is_processed):
        tag = TagForTitleFactory.create()
        tb = TaggingBatchFactory.build(
            source_file=plain_test_file, last_updated_by=users['admin1'], state=state, tag=tag
        )
        tb.save()
        tagging_batch_preflight_task(tb.pk)
        tb.refresh_from_db()
        if is_processed:
            assert tb.state == TaggingBatchState.PREFLIGHT
            assert tb.annotated_file is not None
            assert tb.preflight != {}
        else:
            assert tb.state == state

    @pytest.mark.parametrize(
        ['state', 'is_assigned'],
        [(TaggingBatchState.IMPORTING, True),]
        + [
            (state, False)
            for state in TaggingBatchState.values
            if state != TaggingBatchState.IMPORTING
        ],
    )
    def test_tagging_batch_assign_tag_task(self, inmemory_media, users, state, is_assigned):
        tag = TagForTitleFactory.create()
        tb = TaggingBatchFactory.build(
            source_file=plain_test_file, last_updated_by=users['admin1'], state=state, tag=tag,
        )
        tb.save()
        tagging_batch_assign_tag_task(tb.pk, 'foo')
        tb.refresh_from_db()
        if is_assigned:
            assert tb.state == TaggingBatchState.IMPORTED
            assert tb.postflight != {}
        else:
            assert tb.state == state

    @pytest.mark.parametrize(
        ['state', 'is_undone'],
        [(TaggingBatchState.UNDOING, True),]
        + [
            (state, False)
            for state in TaggingBatchState.values
            if state != TaggingBatchState.UNDOING
        ],
    )
    def test_tagging_batch_unassign_task(self, inmemory_media, users, state, is_undone):
        tag = TagForTitleFactory.create()
        tb = TaggingBatchFactory.build(
            source_file=plain_test_file, last_updated_by=users['admin1'], state=state, tag=tag,
        )
        tb.save()
        with patch('tags.tasks.tagging_batch_preflight_task') as preflight_task:
            tagging_batch_unassign_task(tb.pk)
            if is_undone:
                assert preflight_task.apply_async.called, 'the preflight task should be called'
            else:
                assert (
                    not preflight_task.apply_async.called
                ), 'the preflight task should not be called'
        tb.refresh_from_db()
        if is_undone:
            assert tb.state == TaggingBatchState.INITIAL
        else:
            assert tb.state == state
