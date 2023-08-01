import codecs
import csv
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.files.base import ContentFile
from freezegun import freeze_time
from publications.fake_data import TitleFactory
from publications.tests.test_api import MockTask
from rest_framework.reverse import reverse

from tags.fake_data import (
    TagClassFactory,
    TagFactory,
    TagForTitleFactory,
    TaggingAttemptFactory,
    TaggingBatchFactory,
)
from tags.models import (
    AccessibleBy,
    TaggingAttemptOperation,
    TaggingBatch,
    TaggingBatchState,
    TagScope,
    TitleTag,
)
from tags.tasks import (
    reprocess_due_tagging_batches_task,
    tagging_batch_assign_tag_task,
    tagging_batch_preflight_task,
    tagging_batch_unassign_task,
)
from test_scenarios.basic import (  # noqa - fixtures
    basic1,
    clients,
    data_sources,
    identities,
    organizations,
    platforms,
    users,
)

plain_test_file = Path(__file__).parent / '../../../test-data/tagging_batch/plain-title-list.csv'
plain_test_file_with_tags = (
    Path(__file__).parent / '../../../test-data/tagging_batch/plain-title-list-with-tags.csv'
)
bom_test_file = (
    Path(__file__).parent / '../../../test-data/tagging_batch/simple-title-list-with-bom.csv'
)


@pytest.mark.django_db()
class TestBatchTagging:
    @pytest.mark.parametrize('has_class', [True, False])
    @pytest.mark.parametrize('has_tag', [True, False])
    def test_tagging_batch_preflight(
        self, inmemory_media, has_class, has_tag, django_assert_num_queries
    ):
        TitleFactory.create(isbn='9780787960186')
        TitleFactory.create(issn='1234-5678')
        extra = {}
        if has_class:
            extra['tag_class'] = TagClassFactory.create(scope=TagScope.TITLE)
        if has_tag:
            extra['tag'] = TagForTitleFactory.create(
                tag_class=extra['tag_class']
                if has_class
                else TagClassFactory.create(scope=TagScope.TITLE)
            )
        else:
            extra['tag'] = None  # ensure the factory does not create a random tag
        tb = TaggingBatchFactory.create(
            source_file=plain_test_file, state=TaggingBatchState.PREPROCESSING, **extra
        )
        if has_tag:
            # if we have tag, we can do preflight
            tb.do_preflight()
            assert tb.state == TaggingBatchState.PREFLIGHT
            with django_assert_num_queries(5):
                # each call to last_preflight does 1 query
                # this is here as documentation that it behaves in this way
                assert tb.last_preflight is not None
                assert tb.last_preflight.rows_total == 6
                assert tb.last_preflight.rows_no_match == 3
                assert tb.last_preflight.unique_matched_titles == 2
                assert tb.last_preflight.recognized_columns == ['eISSN', 'ISBN', 'issn']
        elif has_class:
            # we could still do preflight, but we would need to find the tag column in the data
            assert tb.misses_tag_column
            with pytest.raises(
                ValueError, match='The source file does not contain the `tag` column'
            ):
                tb.do_preflight()
        else:
            with pytest.raises(ValueError, match='Either tag or tag_class must be set'):
                tb.do_preflight()

    def test_tagging_batch_preflight_with_bom(self, inmemory_media):
        tb = TaggingBatchFactory.create(
            tag=TagForTitleFactory(),
            source_file=bom_test_file,
            state=TaggingBatchState.PREPROCESSING,
        )
        tb.do_preflight()
        assert tb.state == TaggingBatchState.PREFLIGHT
        assert tb.last_preflight is not None
        assert tb.last_preflight.recognized_columns == ['ISSN']

    def test_tagging_batch_tagging(self, inmemory_media, users):
        TitleFactory.create(isbn='9780787960186')
        TitleFactory.create(issn='1234-5678')
        tag = TagForTitleFactory.create()
        tb = TaggingBatchFactory.create(
            tag=tag, source_file=plain_test_file, last_updated_by=users['admin1']
        )
        tb.do_preflight()
        tb.state = TaggingBatchState.IMPORTING
        tb.assign_tag()
        assert tb.state == TaggingBatchState.IMPORTED
        assert tb.last_import.tagged_titles == 2, "2 are matched by 3 lines"
        assert tag.titles.count() == 2, "2 are matched by 3 lines"

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
        assert tb.last_import.unique_matched_titles == 2
        assert tb.titletag_set.count() == 1, 'only one titletag'
        assert tb.last_import.tagged_titles == 1

    @pytest.mark.parametrize('exclusive', [True, False])
    def test_tagging_with_existing_tags_and_exclusive_tags(self, inmemory_media, users, exclusive):
        t1 = TitleFactory.create(isbn='9780787960186')
        t2 = TitleFactory.create(issn='1234-5678')
        tc = TagClassFactory.create(exclusive=exclusive, scope=TagScope.TITLE)
        tag1 = TagForTitleFactory.create(tag_class=tc)
        tag2 = TagForTitleFactory.create(tag_class=tc)
        tag1.tag(t1, users['admin1'])  # t1 has a different exclusive tag
        tag2.tag(t2, users['admin1'])  # t2 already has the tag
        assert TitleTag.objects.count() == 2
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
        if exclusive:
            assert t1.tags.count() == 1, 't1 should have only the first tag'
            assert t1.tags.all()[0] == tag1, 't1 should have the first tag'
            assert t2.tags.count() == 1, 't2 should be tagged with the second tag'
            assert t2.tags.all()[0] == tag2, 't2 should have the second tag'
            assert tb.titletag_set.count() == 0, 'no new tagged title'
            assert tb.last_import.unique_matched_titles == 2
            assert tb.last_import.tagged_titles == 0
            assert tb.last_import.already_tagged_titles == 1
            assert tb.last_import.exclusively_tagged_titles == 1
        else:
            assert t1.tags.count() == 2, 't1 should both tags'
            assert t2.tags.count() == 1, 't2 should be tagged with the second tag'
            assert t2.tags.all()[0] == tag2, 't2 should have the second tag'
            assert tb.titletag_set.count() == 1, '1 new tagged title'
            assert tb.last_import.unique_matched_titles == 2
            assert tb.last_import.tagged_titles == 1
            assert tb.last_import.already_tagged_titles == 1
            assert tb.last_import.exclusively_tagged_titles == 0

    def test_batch_tagging_file_content(self, inmemory_media, users):
        """
        Test that an annotated_file is correctly created during preflight and processing
        """
        TitleFactory.create(isbn='9780787960186')
        TitleFactory.create(issn='1234-5678')

        tb = TaggingBatchFactory.create(
            tag=TagForTitleFactory.create(),
            source_file=plain_test_file,
            last_updated_by=users['admin1'],
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
        tb.state = TaggingBatchState.IMPORTING
        tb.assign_tag()
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
        tag = TagForTitleFactory.create()
        tb = TaggingBatchFactory.create(
            tag=tag, source_file=plain_test_file, last_updated_by=users['admin1']
        )
        tb.do_preflight()
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
        assert tb.taggingattempts.count() == 0, 'add attempts were removed'

    def test_tagging_batch_second_tagging(self, inmemory_media, users):
        TitleFactory.create(isbn='9780787960186')
        TitleFactory.create(issn='1234-5678')
        tag = TagForTitleFactory.create()
        tb = TaggingBatchFactory.create(
            tag=tag, source_file=plain_test_file, last_updated_by=users['admin1']
        )
        tb.do_preflight()
        tb.state = TaggingBatchState.IMPORTING
        assert tb.preflights.count() == 1
        assert tb.imports.count() == 0
        tb.assign_tag()
        assert tb.preflights.count() == 1
        assert tb.imports.count() == 1
        assert tag.titles.count() == 2, 'two titles are tagged'
        # add a new title which will be matched by the file
        TitleFactory.create(issn='2546-5794')
        tb.state = TaggingBatchState.IMPORTING
        tb.assign_tag()
        assert tb.preflights.count() == 1
        assert tb.imports.count() == 2
        assert tb.last_import.unique_matched_titles == 3
        assert tb.last_import.already_tagged_titles == 2
        assert tb.last_import.tagged_titles == 1


@pytest.mark.django_db()
class TestBatchTaggingWithTagsInFile:
    @pytest.mark.parametrize(
        ['issn', 'used_tags'],
        [
            ('1234-5678', {'hroch': 2, 'prase': 1, 'praze': 2}),
            ('1234-5679', {'hroch': 0, 'prase': 1, 'praze': 0}),
            # issn matches the same two titles from two lines
            ('2546-5794', {'hroch': 0, 'prase': 3, 'praze': 0}),
        ],
    )
    def test_tagging_batch_preflight(self, inmemory_media, issn, used_tags):
        TitleFactory.create(isbn='9780787960186')
        TitleFactory.create(name='foo', issn=issn)
        TitleFactory.create(name='bar', eissn=issn)
        tb = TaggingBatchFactory.create(
            tag_class=TagClassFactory.create(scope=TagScope.TITLE),
            source_file=plain_test_file_with_tags,
            state=TaggingBatchState.PREPROCESSING,
        )
        # we could do preflight, if there are tags in the file
        assert not tb.misses_tag_column
        tb.do_preflight()
        assert tb.state == TaggingBatchState.PREFLIGHT
        preflight = tb.last_preflight
        assert set(preflight.tag_stats.keys()) == {'hroch', 'prase', 'praze'}
        assert all(
            {'matched_lines', 'matched_titles'} == set(rec.keys())
            for rec in preflight.tag_stats.values()
        )
        # the following is the same regardless of existing titles
        assert {name: rec['matched_lines'] for name, rec in preflight.tag_stats.items()} == {
            'hroch': 1,
            'prase': 4,
            'praze': 1,
        }
        # the following depends on existing titles
        assert {
            name: rec['matched_titles'] for name, rec in preflight.tag_stats.items()
        } == used_tags
        assert preflight.rows_no_tag == 1

    @pytest.mark.parametrize(
        ['issn', 'tag_stats'],
        [
            ('1234-5678', {'hroch': 2, 'prase': 1, 'praze': 2}),
            ('1234-5679', {'hroch': 0, 'prase': 1, 'praze': 0}),
            # issn matches the same two titles from two lines
            ('2546-5794', {'hroch': 0, 'prase': 3, 'praze': 0}),
        ],
    )
    def test_tagging_batch_tagging(self, inmemory_media, users, issn, tag_stats):
        TitleFactory.create(isbn='9780787960186')
        TitleFactory.create(issn=issn)
        TitleFactory.create(eissn=issn)
        tc = TagClassFactory.create(scope=TagScope.TITLE)
        tb = TaggingBatchFactory.create(
            tag_class=tc,
            source_file=plain_test_file_with_tags,
            state=TaggingBatchState.PREPROCESSING,
        )
        tb.do_preflight()
        assert tb.state == TaggingBatchState.PREFLIGHT
        tb.state = TaggingBatchState.IMPORTING
        assert tc.tag_set.count() == 0
        assert TitleTag.objects.count() == 0
        tb.assign_tag()
        assert tb.state == TaggingBatchState.IMPORTED
        used_tags = [tag for tag, count in tag_stats.items() if count > 0]
        assert tc.tag_set.count() == len(used_tags)
        assert TitleTag.objects.count() == sum(tag_stats.values())
        tb_tag_stats = tb.last_import.tag_stats
        assert set(tb_tag_stats.keys()) == {'hroch', 'prase', 'praze'}
        assert all(
            {'matched_lines', 'matched_titles', 'tagged_titles'} == set(rec.keys())
            for rec in tb_tag_stats.values()
        )
        # matched_lines are the same regardless of existing titles
        assert {name: rec['matched_lines'] for name, rec in tb_tag_stats.items()} == {
            'hroch': 1,
            'prase': 4,
            'praze': 1,
        }
        # matched_titles depend on existing titles
        assert {name: rec['matched_titles'] for name, rec in tb_tag_stats.items()} == tag_stats
        # tagged_titles depend on existing titles
        assert {name: rec['tagged_titles'] for name, rec in tb_tag_stats.items()} == tag_stats
        # test recognized columns
        assert set(tb.last_import.recognized_columns) == {'issn', 'eISSN', 'ISBN'}
        # test un-assign as well
        tb.state = TaggingBatchState.UNDOING
        tb.unassign_tag()
        assert tc.tag_set.count() == len(used_tags), 'tags are not deleted'
        assert TitleTag.objects.count() == 0, 'title tags are deleted - titles untagged'

    def test_tagging_batch_retagging(self, inmemory_media, users):
        """
        Test that the second attempt of tagging the same file does not create duplicate tags
        and has correct stats
        """
        tc = TagClassFactory.create(scope=TagScope.TITLE)
        tb = TaggingBatchFactory.create(
            tag_class=tc,
            source_file=plain_test_file_with_tags,
            state=TaggingBatchState.PREPROCESSING,
        )
        TitleFactory.create(issn='2546-5794')
        tb.do_preflight()
        assert tb.state == TaggingBatchState.PREFLIGHT
        tb.state = TaggingBatchState.IMPORTING
        assert tc.tag_set.count() == 0
        assert TitleTag.objects.count() == 0
        tb.assign_tag()
        assert tb.state == TaggingBatchState.IMPORTED
        assert tb.imports.count() == 1, 'one import'
        # matched_titles depend on existing titles
        assert {name: rec['matched_titles'] for name, rec in tb.last_import.tag_stats.items()} == {
            'hroch': 0,
            'prase': 1,
            'praze': 0,
        }
        assert {name: rec['tagged_titles'] for name, rec in tb.last_import.tag_stats.items()} == {
            'hroch': 0,
            'prase': 1,
            'praze': 0,
        }

        # create some more titles
        TitleFactory.create(isbn='9780787960186')
        TitleFactory.create(eissn='2546-5794')
        # re-assign tag
        tb.state = TaggingBatchState.IMPORTING
        tb.assign_tag()
        assert tb.state == TaggingBatchState.IMPORTED, 'state is still IMPORTED'
        assert tb.imports.count() == 2, 'two imports now'
        # matched_titles contains all matched titles regardless if they have been tagged already
        assert {name: rec['matched_titles'] for name, rec in tb.last_import.tag_stats.items()} == {
            'hroch': 0,
            'prase': 3,
            'praze': 0,
        }
        # tagged_titles contains only titles that have been tagged in this attempt
        assert {name: rec['tagged_titles'] for name, rec in tb.last_import.tag_stats.items()} == {
            'hroch': 0,
            'prase': 2,
            'praze': 0,
        }

    @pytest.mark.parametrize(
        ['existing_issns', 'tagged_issns', 'value'],
        [
            (['1234-5678'], ['1234-5678'], 1),
            (['1234-5678', '2546-5794'], [], 0),
            (['1234-5678', '2546-5794'], ['1234-5678'], 1),
            (['1234-5678', '2546-5794'], ['2546-5794'], 1),
            (['1234-5678', '2546-5794'], ['1234-5678', '2546-5794'], 2),
        ],
    )
    def test_exclusively_tagged_titles_computation_tag(
        self, inmemory_media, users, existing_issns, tagged_issns, value
    ):
        """
        `exclusively_tagged_titles` is a stat that should tell the user how many titles had already
        been tagged by a different tag from an exclusive tag class.

        Because it is not straightforward to compute this number, this test is here to document the
        process.

        This test is for tagging batches with one specific tag set.
        """
        issn_to_title = {}
        for issn in existing_issns:
            issn_to_title[issn] = TitleFactory.create(issn=issn)
        tc = TagClassFactory.create(exclusive=True, scope=TagScope.TITLE)
        tag1 = TagForTitleFactory.create(tag_class=tc, name='foo')
        for issn in tagged_issns:
            tag1.tag(issn_to_title[issn], users['admin1'])
        tag2 = TagForTitleFactory.create(tag_class=tc, name='bar')
        tb = TaggingBatchFactory.create(
            tag=tag2,
            source_file=plain_test_file_with_tags,
            state=TaggingBatchState.PREPROCESSING,
        )
        tb.state = TaggingBatchState.IMPORTING
        tb.assign_tag()
        assert tb.state == TaggingBatchState.IMPORTED
        assert tb.last_import.exclusively_tagged_titles == value

    @pytest.mark.parametrize(
        ['existing_issns', 'tagged_issns', 'value'],
        [
            (['1234-5678'], ['1234-5678'], 1),
            (['1234-5678', '2546-5794'], [], 0),
            (['1234-5678', '2546-5794'], ['1234-5678'], 1),
            (['1234-5678', '2546-5794'], ['2546-5794'], 1),
            (['1234-5678', '2546-5794'], ['1234-5678', '2546-5794'], 2),
        ],
    )
    def test_exclusively_tagged_titles_computation_tag_class(
        self, inmemory_media, users, existing_issns, tagged_issns, value
    ):
        """
        `exclusively_tagged_titles` is a stat that should tell the user how many titles had already
        been tagged by a different tag from an exclusive tag class.

        Because it is not straightforward to compute this number, this test is here to document the
        process.

        This test is for tagging batches with tag_class set, not tag.
        """
        issn_to_title = {}
        for issn in existing_issns:
            issn_to_title[issn] = TitleFactory.create(issn=issn)
        tc = TagClassFactory.create(exclusive=True, scope=TagScope.TITLE)
        tag1 = TagForTitleFactory.create(tag_class=tc, name='foo')
        for issn in tagged_issns:
            tag1.tag(issn_to_title[issn], users['admin1'])
        tb = TaggingBatchFactory.create(
            tag_class=tc,
            source_file=plain_test_file_with_tags,
            state=TaggingBatchState.PREPROCESSING,
        )
        tb.state = TaggingBatchState.IMPORTING
        tb.assign_tag()
        assert tb.state == TaggingBatchState.IMPORTED
        assert tb.last_import.exclusively_tagged_titles == value


@pytest.mark.django_db()
class TestBatchTaggingAPI:
    @pytest.mark.parametrize(
        'client_type',
        [
            'user1',
            'user2',
            'admin1',
            'admin2',
            'master_admin',
            'master_user',
            'su',
        ],
    )
    @pytest.mark.parametrize(
        ['owner_type', 'access_level', 'org_name', 'allowed_users'],
        [
            ('user1', AccessibleBy.OWNER, None, ['user1']),
            ('user2', AccessibleBy.OWNER, None, ['user2']),
            ('admin1', AccessibleBy.OWNER, None, ['admin1']),
            ('admin2', AccessibleBy.OWNER, None, ['admin2']),
            ('master_admin', AccessibleBy.OWNER, None, ['master_admin']),
            ('master_user', AccessibleBy.OWNER, None, ['master_user']),
            ('su', AccessibleBy.OWNER, None, ['su']),
            (
                'admin1',
                AccessibleBy.ORG_USERS,
                'root',
                ['admin1', 'master_user', 'master_admin', 'su'],
            ),
            (
                'admin2',
                AccessibleBy.ORG_USERS,
                'standalone',
                ['admin2', 'user2', 'master_user', 'master_admin', 'su'],
            ),
            ('admin1', AccessibleBy.ORG_ADMINS, 'root', ['admin1', 'master_admin', 'su']),
            ('admin2', AccessibleBy.ORG_ADMINS, 'standalone', ['admin2', 'master_admin', 'su']),
            ('master_admin', AccessibleBy.CONS_ADMINS, None, ['master_admin', 'su']),
            ('su', AccessibleBy.CONS_ADMINS, None, ['master_admin', 'su']),
            (
                'master_admin',
                AccessibleBy.EVERYBODY,
                None,
                ['user1', 'user2', 'admin1', 'admin2', 'master_admin', 'master_user', 'su'],
            ),
        ],
    )
    def test_tagging_batch_visibility_one_tag(
        self,
        inmemory_media,
        clients,
        users,
        owner_type,
        access_level,
        org_name,
        allowed_users,
        client_type,
        basic1,
    ):
        """
        Test that the tagging batch visibility matches that of the corresponding tag
        """
        extra = {'owner_org': basic1['organizations'][org_name]} if org_name else {}
        tag = TagForTitleFactory.create(
            can_assign=access_level, can_see=access_level, owner=users[owner_type], **extra
        )
        tb = TaggingBatchFactory.create(
            tag=tag, source_file=plain_test_file, last_updated_by=users[owner_type]
        )
        # test the detail endpoint
        resp = clients[client_type].get(reverse('tagging-batch-detail', args=[tb.pk]))
        assert resp.status_code == (200 if client_type in allowed_users else 404)
        # test the list endpoint
        resp = clients[client_type].get(reverse('tagging-batch-list'))
        assert resp.status_code == 200
        sees_tb = any(rec['pk'] == tb.pk for rec in resp.json())
        assert sees_tb == (client_type in allowed_users)

    @pytest.mark.parametrize(
        'client_type',
        [
            'user1',
            'user2',
            'admin1',
            'admin2',
            'master_admin',
            'master_user',
            'su',
        ],
    )
    @pytest.mark.parametrize(
        ['owner_type', 'access_level', 'org_name', 'allowed_users'],
        [
            ('user1', AccessibleBy.OWNER, None, ['user1']),
            ('user2', AccessibleBy.OWNER, None, ['user2']),
            ('admin1', AccessibleBy.OWNER, None, ['admin1']),
            ('admin2', AccessibleBy.OWNER, None, ['admin2']),
            ('master_admin', AccessibleBy.OWNER, None, ['master_admin']),
            ('master_user', AccessibleBy.OWNER, None, ['master_user']),
            ('su', AccessibleBy.OWNER, None, ['su']),
            (
                'admin1',
                AccessibleBy.ORG_USERS,
                'root',
                ['admin1', 'master_user', 'master_admin', 'su'],
            ),
            (
                'admin2',
                AccessibleBy.ORG_USERS,
                'standalone',
                ['admin2', 'user2', 'master_user', 'master_admin', 'su'],
            ),
            ('admin1', AccessibleBy.ORG_ADMINS, 'root', ['admin1', 'master_admin', 'su']),
            ('admin2', AccessibleBy.ORG_ADMINS, 'standalone', ['admin2', 'master_admin', 'su']),
            ('master_admin', AccessibleBy.CONS_ADMINS, None, ['master_admin', 'su']),
            ('su', AccessibleBy.CONS_ADMINS, None, ['master_admin', 'su']),
            (
                'master_admin',
                AccessibleBy.EVERYBODY,
                None,
                ['user1', 'user2', 'admin1', 'admin2', 'master_admin', 'master_user', 'su'],
            ),
        ],
    )
    def test_tagging_batch_visibility_tag_class(
        self,
        inmemory_media,
        clients,
        users,
        owner_type,
        access_level,
        org_name,
        allowed_users,
        client_type,
        basic1,
    ):
        """
        Test that the tagging batch visibility matches that of the corresponding tag_class
        if there is no tag
        """
        extra = {'owner_org': basic1['organizations'][org_name]} if org_name else {}
        tc = TagClassFactory.create(
            scope=TagScope.TITLE,
            default_tag_can_assign=access_level,
            owner=users[owner_type],
            **extra,
        )
        tb = TaggingBatchFactory.create(
            tag_class=tc, source_file=plain_test_file, last_updated_by=users[owner_type]
        )
        # test the detail endpoint
        resp = clients[client_type].get(reverse('tagging-batch-detail', args=[tb.pk]))
        assert resp.status_code == (200 if client_type in allowed_users else 404)
        # test the list endpoint
        resp = clients[client_type].get(reverse('tagging-batch-list'))
        assert resp.status_code == 200
        sees_tb = any(rec['pk'] == tb.pk for rec in resp.json())
        assert sees_tb == (client_type in allowed_users)

    @pytest.mark.parametrize('send_existing_tag', [True, False, None])
    def test_tagging_batch_create_with_tag(self, inmemory_media, clients, users, send_existing_tag):
        """
        Test that creating a tagging batch with a tag works.
        The upload must have a file and a tag (or tag_class).
        `send_existing_tag`:
            True - send an existing tag class
            False - send a non-existing tag class
            None - do not send a tag class
        """
        tag = TagForTitleFactory.create()
        with plain_test_file.open('rb') as infile, patch(
            'tags.views.tagging_batch_preflight_task'
        ) as preflight_task:
            tag_id = tag.pk + (0 if send_existing_tag else 1)  # +1 means non-existent ID
            extra = {'tag': tag_id} if send_existing_tag is not None else {}
            resp = clients['admin1'].post(
                reverse('tagging-batch-list'), {'source_file': infile, **extra}
            )
            assert (
                not preflight_task.delay.called
            ), 'preflight should not be started on batch creation'
            assert (
                not preflight_task.apply_async.called
            ), 'preflight should not be started on batch creation'
        assert resp.status_code == (201 if send_existing_tag else 400)
        if send_existing_tag:
            tb = TaggingBatch.objects.get()
            assert resp.json()['pk'] == tb.pk
            assert tb.last_updated_by == users['admin1']
            assert resp.json()['tag']['pk'] == tb.tag_id

    @pytest.mark.parametrize('send_existing_tagclass', [True, False, None])
    def test_tagging_batch_create_with_tag_class(
        self, inmemory_media, clients, users, send_existing_tagclass
    ):
        """
        Test that creating a tagging batch with a tag class works.
        The upload must have a file and a tag_class (or tag).
        `send_existing_tagclass`:
            True - send an existing tag class
            False - send a non-existing tag class
            None - do not send a tag class
        """
        tc = TagClassFactory.create(scope=TagScope.TITLE)
        with plain_test_file.open('rb') as infile, patch(
            'tags.views.tagging_batch_preflight_task'
        ) as preflight_task:
            tc_id = tc.pk + (0 if send_existing_tagclass else 1)  # +1 means non-existent ID
            extra = {'tag_class': tc_id} if send_existing_tagclass is not None else {}
            resp = clients['admin1'].post(
                reverse('tagging-batch-list'), {'source_file': infile, **extra}
            )
            assert (
                not preflight_task.delay.called
            ), 'preflight should not be started on batch creation'
            assert (
                not preflight_task.apply_async.called
            ), 'preflight should not be started on batch creation'
        assert resp.status_code == (201 if send_existing_tagclass else 400)
        if send_existing_tagclass:
            tb = TaggingBatch.objects.get()
            assert resp.json()['pk'] == tb.pk
            assert tb.last_updated_by == users['admin1']
            assert resp.json()['tag_class']['pk'] == tb.tag_class_id

    @pytest.mark.parametrize(
        'client_type',
        [
            'user1',
            'user2',
            'admin1',
            'admin2',
            'master_admin',
            'master_user',
            'su',
        ],
    )
    def test_tagging_batch_create_tag_access_restrictions(
        self, inmemory_media, clients, users, client_type
    ):
        """
        Test that creating a tagging batch with a tag properly checks the permissions of the user
        for that tag.
        """
        tag = TagForTitleFactory.create(owner=users['user2'], can_assign=AccessibleBy.OWNER)
        with plain_test_file.open('rb') as infile:
            resp = clients[client_type].post(
                reverse('tagging-batch-list'), {'source_file': infile, 'tag': tag.pk}
            )
        assert resp.status_code == (201 if client_type == 'user2' else 403)

    @pytest.mark.parametrize(
        'client_type',
        [
            'user1',
            'user2',
            'admin1',
            'admin2',
            'master_admin',
            'master_user',
            'su',
        ],
    )
    def test_tagging_batch_create_tag_class_access_restrictions(
        self, inmemory_media, clients, users, client_type
    ):
        """
        Test that creating a tagging batch with a tag properly checks the permissions of the user
        for that tag.
        """
        tc = TagClassFactory.create(
            scope=TagScope.TITLE, owner=users['user2'], default_tag_can_assign=AccessibleBy.OWNER
        )
        with plain_test_file.open('rb') as infile:
            resp = clients[client_type].post(
                reverse('tagging-batch-list'), {'source_file': infile, 'tag_class': tc.pk}
            )
        assert resp.status_code == (201 if client_type == 'user2' else 403)

    @pytest.mark.parametrize(
        ('tag_scope', 'can_create'),
        [
            (TagScope.TITLE, True),
            (TagScope.PLATFORM, False),
            (TagScope.ORGANIZATION, False),
        ],
    )
    def test_tagging_batch_create_tag_scope_restrictions(
        self, inmemory_media, clients, users, tag_scope, can_create
    ):
        """
        Test that creating a tagging batch with a tag properly checks the permissions of the user
        for that tag.
        """
        tag = TagFactory.create(
            tag_class__scope=tag_scope, owner=users['user2'], can_assign=AccessibleBy.OWNER
        )
        with plain_test_file.open('rb') as infile:
            resp = clients['user2'].post(
                reverse('tagging-batch-list'), {'source_file': infile, 'tag': tag.pk}
            )
        assert resp.status_code == (201 if can_create else 400)

    @pytest.mark.parametrize(
        ('tag_scope', 'can_create'),
        [
            (TagScope.TITLE, True),
            (TagScope.PLATFORM, False),
            (TagScope.ORGANIZATION, False),
        ],
    )
    def test_tagging_batch_create_tag_class_scope_restrictions(
        self, inmemory_media, clients, users, tag_scope, can_create
    ):
        """
        Test that creating a tagging batch with a tag properly checks the permissions of the user
        for that tag.
        """
        tc = TagClassFactory.create(
            scope=tag_scope, owner=users['user2'], default_tag_can_assign=AccessibleBy.OWNER
        )
        with plain_test_file.open('rb') as infile:
            resp = clients['user2'].post(
                reverse('tagging-batch-list'), {'source_file': infile, 'tag_class': tc.pk}
            )
        assert resp.status_code == (201 if can_create else 400)

    @pytest.mark.parametrize(
        ['existing_tb', 'tb_state', 'status_code'],
        [
            (True, TaggingBatchState.INITIAL, 202),
            (True, TaggingBatchState.PREPROCESSING, 400),
            (True, TaggingBatchState.PREFLIGHT, 400),
            (True, TaggingBatchState.PREFAILED, 400),
            (False, TaggingBatchState.INITIAL, 404),
        ],
    )
    def test_tagging_batch_preflight(
        self, inmemory_media, clients, users, existing_tb, tb_state, status_code
    ):
        # prepare the batch
        TitleFactory.create(isbn='9780787960186')
        TitleFactory.create(issn='1234-5678')
        tag = TagForTitleFactory.create()
        tb = TaggingBatchFactory.create(
            tag=tag, source_file=plain_test_file, last_updated_by=users['admin1']
        )
        tb.state = tb_state
        tb.save()
        with patch('tags.views.tagging_batch_preflight_task') as preflight_task:
            preflight_task.apply_async.return_value = MockTask()
            resp = clients['admin1'].post(
                reverse('tagging-batch-preflight', args=[tb.pk if existing_tb else tb.pk + 1])
            )
            assert resp.status_code == status_code
            if status_code == 202:
                assert preflight_task.apply_async.called, 'the tagging task should be started'
                tb.refresh_from_db()
                assert tb.state == TaggingBatchState.PREPROCESSING
            else:
                assert (
                    not preflight_task.apply_async.called
                ), 'the tagging task should not be started'

    @pytest.mark.parametrize(
        ['existing_tb', 'tb_state', 'status_code'],
        [
            (False, TaggingBatchState.PREFLIGHT, 404),
            (True, TaggingBatchState.INITIAL, 400),
            (True, TaggingBatchState.PREFAILED, 400),
            (True, TaggingBatchState.IMPORTED, 202),  # imported can be re-imported
            (True, TaggingBatchState.IMPORTING, 400),
            (True, TaggingBatchState.PREFLIGHT, 202),  # preflight can be imported
        ],
    )
    def test_tagging_batch_tagging(
        self, inmemory_media, clients, users, existing_tb, tb_state, status_code
    ):
        # prepare the batch
        TitleFactory.create(isbn='9780787960186')
        TitleFactory.create(issn='1234-5678')
        tag = TagForTitleFactory.create()
        tb = TaggingBatchFactory.create(
            tag=tag, source_file=plain_test_file, last_updated_by=users['admin1']
        )
        if tb_state not in [TaggingBatchState.INITIAL, TaggingBatchState.PREFAILED]:
            tb.do_preflight()
        tb.state = tb_state
        tb.save()
        # apply a tag to all the titles
        with patch('tags.views.tagging_batch_assign_tag_task') as tagging_task:
            tagging_task.apply_async.return_value = MockTask()
            resp = clients['admin1'].post(
                reverse('tagging-batch-assign-tags', args=[tb.pk if existing_tb else tb.pk + 1])
            )
            assert resp.status_code == status_code
            if status_code == 202:
                tagging_task.apply_async.assert_called(), 'the tagging task should be started'
                tb.refresh_from_db()
                assert tb.state == TaggingBatchState.IMPORTING

    def test_tagging_batch_retagging(self, inmemory_media, clients, users):
        """
        Tests that it is possible to re-tag a batch possibly matching newly arrived titles
        """
        # prepare the batch
        TitleFactory.create(isbn='9780787960186')
        TitleFactory.create(issn='1234-5678')
        tag = TagForTitleFactory.create()
        tb = TaggingBatchFactory.create(
            tag=tag,
            source_file=plain_test_file,
            last_updated_by=users['admin1'],
            state=TaggingBatchState.PREFLIGHT,
        )
        tb.do_preflight()
        tb.state = TaggingBatchState.IMPORTING
        tb.assign_tag()
        assert tb.state == TaggingBatchState.IMPORTED
        # apply a tag to all the titles
        with patch('tags.views.tagging_batch_assign_tag_task') as tagging_task:
            tagging_task.apply_async.return_value = MockTask()
            resp = clients['admin1'].post(reverse('tagging-batch-assign-tags', args=[tb.pk]))
            assert resp.status_code == 202
            tagging_task.apply_async.assert_called(), 'the tagging task should be started'
            tb.refresh_from_db()
            assert tb.state == TaggingBatchState.IMPORTING

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
        assert tag.titles.count() == 0, 'the tag was also removed from the titles'

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
        tag = TagForTitleFactory.create(owner=users['user2'], can_assign=AccessibleBy.OWNER)
        tb = TaggingBatchFactory.create(
            tag=tag, source_file=plain_test_file, last_updated_by=users['user2']
        )
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

    def test_tagging_batch_list(self, inmemory_media, clients, users):
        tag = TagForTitleFactory.create(owner=users['user2'])
        tb = TaggingBatchFactory.create(
            tag=tag, source_file=plain_test_file, last_updated_by=users['user2']
        )
        # preliminary test that it works without any attempt
        resp = clients['user2'].get(reverse('tagging-batch-list'))
        assert resp.status_code == 200
        # create some attempts
        *_x, preflight = TaggingAttemptFactory.create_batch(
            3, batch=tb, operation=TaggingAttemptOperation.PREFLIGHT
        )
        *_x, postflight = TaggingAttemptFactory.create_batch(
            3, batch=tb, operation=TaggingAttemptOperation.IMPORT
        )
        # and test it
        resp = clients['user2'].get(reverse('tagging-batch-list'))
        assert len(resp.json()) == 1
        tb_data = resp.json()[0]
        assert tb_data['pk'] == tb.pk
        assert tb_data['preflight']['pk'] == preflight.pk
        assert tb_data['postflight']['pk'] == postflight.pk

    def test_tagging_batch_patch_reprocess_after(self, inmemory_media, clients, users):
        tb = TaggingBatchFactory.create(source_file=plain_test_file, last_updated_by=users['user2'])
        # set the reprocess_after to 30 days
        resp = clients['user2'].patch(
            reverse('tagging-batch-detail', args=[tb.pk]),
            {'reprocess_after': '30 days'},
            format='json',
        )
        assert resp.status_code == 200
        tb.refresh_from_db()
        assert tb.reprocess_after == timedelta(days=30)
        # set it to None
        resp = clients['user2'].patch(
            reverse('tagging-batch-detail', args=[tb.pk]), {'reprocess_after': None}, format='json'
        )
        assert resp.status_code == 200
        tb.refresh_from_db()
        assert tb.reprocess_after is None


@pytest.mark.django_db()
class TestTasks:
    @pytest.mark.parametrize(
        ['state', 'is_processed'],
        [(TaggingBatchState.PREPROCESSING, True)]
        + [
            (state, False)
            for state in TaggingBatchState.values
            if state != TaggingBatchState.PREPROCESSING
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
            assert tb.last_preflight is not None
        else:
            assert tb.state == state

    @pytest.mark.parametrize(
        ['state', 'is_assigned'],
        [(TaggingBatchState.IMPORTING, True)]
        + [
            (state, False)
            for state in TaggingBatchState.values
            if state != TaggingBatchState.IMPORTING
        ],
    )
    def test_tagging_batch_assign_tag_task(self, inmemory_media, users, state, is_assigned):
        tag = TagForTitleFactory.create()
        tb = TaggingBatchFactory.build(
            source_file=plain_test_file, last_updated_by=users['admin1'], state=state, tag=tag
        )
        tb.save()
        tagging_batch_assign_tag_task(tb.pk, 'foo')
        tb.refresh_from_db()
        if is_assigned:
            assert tb.state == TaggingBatchState.IMPORTED
            assert tb.last_import is not None
        else:
            assert tb.state == state

    @pytest.mark.parametrize(
        ['state', 'is_undone'],
        [(TaggingBatchState.UNDOING, True)]
        + [
            (state, False)
            for state in TaggingBatchState.values
            if state != TaggingBatchState.UNDOING
        ],
    )
    def test_tagging_batch_unassign_task(self, inmemory_media, users, state, is_undone):
        tag = TagForTitleFactory.create()
        tb = TaggingBatchFactory.build(
            source_file=plain_test_file, last_updated_by=users['admin1'], state=state, tag=tag
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
            assert tb.state == TaggingBatchState.PREPROCESSING
        else:
            assert tb.state == state

    def test_regular_reprocessing(self):
        """
        Test that when a tagging batch has `reprocess_after` set, it will be reprocessed
        in a celery task.
        """
        # create a tagging batch that should be reprocessed
        with freeze_time('2023-01-30'):
            tb1 = TaggingBatchFactory.create(
                reprocess_after=timedelta(days=1), state=TaggingBatchState.IMPORTED
            )
            TaggingAttemptFactory.create(batch=tb1)
        with freeze_time('2023-01-01'):
            # and one more
            tb2 = TaggingBatchFactory.create(
                reprocess_after=timedelta(days=30), state=TaggingBatchState.IMPORTED
            )
            TaggingAttemptFactory.create(batch=tb2)
            # two that should not be reprocessed
            TaggingBatchFactory.create(
                reprocess_after=timedelta(days=1), state=TaggingBatchState.PREFLIGHT
            )  # not imported yet, no reprocess
            TaggingBatchFactory.create(reprocess_after=None)  # no reprocess
        # testing
        with freeze_time('2023-02-02'):
            assert TaggingBatch.objects.to_reprocess().count() == 2
            # do retagging number 1
            with patch('tags.tasks.TaggingBatch.assign_tag') as assign_tag_mock, patch(
                'tags.tasks.reprocess_due_tagging_batches_task.delay'
            ) as task_delay_mock:
                # we create an attempt to simulate what would happen inside `assign_tag`
                assign_tag_mock.side_effect = lambda *args, **kwargs: TaggingAttemptFactory.create(
                    batch=tb1
                )
                reprocess_due_tagging_batches_task()
                assert task_delay_mock.call_count == 1, 'task is requeued'
                assert assign_tag_mock.call_count == 1, 'one batch is reprocessed'
                assert TaggingBatch.objects.to_reprocess().count() == 1
            # do retagging number 2
            with patch('tags.tasks.TaggingBatch.assign_tag') as assign_tag_mock, patch(
                'tags.tasks.reprocess_due_tagging_batches_task.delay'
            ) as task_delay_mock:
                assign_tag_mock.side_effect = lambda *args, **kwargs: TaggingAttemptFactory.create(
                    batch=tb2
                )
                reprocess_due_tagging_batches_task()
                assert task_delay_mock.call_count == 0, 'task is not requeued'
                assert assign_tag_mock.call_count == 1, 'one batch is reprocessed'
                assert TaggingBatch.objects.to_reprocess().count() == 0
