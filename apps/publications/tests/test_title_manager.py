from collections import Counter

import pytest
from django.db.models import Count

from logs.logic.data_import import TitleManager, TitleRec
from logs.logic.validation import normalize_isbn, normalize_title
from nigiri.counter5 import Counter5ReportBase
from publications.models import Title
from test_fixtures.entities.counter_records import CounterRecordFactory


@pytest.mark.django_db
class TestTitleManager:
    def test_mangled_isbn(self):
        """
        Test for a bug that TitleManager looks for data in database with non-normalized isbn
        but uses normalized ISBN when storing new data. This discrepancy may lead to
        database level integrity error because of constraints.
        :return:
        """
        Title.objects.create(name='Foo', isbn='978-0-07-174521-5')
        tm = TitleManager()
        record = TitleRec(
            name='Foo', isbn='978- 0-07-174521-5', issn='', eissn='', doi='', pub_type='U'
        )
        record = tm.normalize_title_rec(record)
        tm.prefetch_titles(records=[record])
        tm.get_or_create(record)

    def test_resolve_unknown_title_pub_types_in_db(self):
        Title.objects.create(
            name='Book',
            isbn='0-8037-4412-9',
            issn='',
            eissn='',
            doi='',
            pub_type=Title.PUB_TYPE_UNKNOWN,
        )
        Title.objects.create(
            name='Book with DOI',
            isbn='0-5312-8211-2',
            issn='',
            eissn='',
            doi='https://dx.doi.org/10.0000/test',
            pub_type=Title.PUB_TYPE_UNKNOWN,
        )
        Title.objects.create(
            name='Journal',
            isbn='',
            issn='1111-2222',
            eissn='',
            doi='',
            pub_type=Title.PUB_TYPE_UNKNOWN,
        )
        Title.objects.create(
            name='eJournal',
            isbn='',
            issn='',
            eissn='3333-4444',
            doi='',
            pub_type=Title.PUB_TYPE_UNKNOWN,
        )
        Title.objects.create(
            name='Hybrid',
            isbn='0-7660-9350-6',
            issn='1111-2222',
            eissn='',
            doi='',
            pub_type=Title.PUB_TYPE_UNKNOWN,
        )
        assert Title.objects.count() == 5
        assert Title.objects.filter(pub_type=Title.PUB_TYPE_UNKNOWN).count() == 5
        TitleManager.resolve_unknown_title_pub_types_in_db()
        assert (
            list(Title.objects.order_by('pub_type').values('pub_type').annotate(count=Count('id')))
        ) == [
            {'pub_type': Title.PUB_TYPE_BOOK, 'count': 2},
            {'pub_type': Title.PUB_TYPE_JOURNAL, 'count': 2},
            {'pub_type': Title.PUB_TYPE_UNKNOWN, 'count': 1},
        ]

    @pytest.mark.parametrize(['reverse'], [(True,), (False,)])  # reverses order of titles bellow
    @pytest.mark.parametrize(
        ['db_title', 'in_title', 'merge'],
        [
            pytest.param({'name': 'AAA'}, {'name': 'AAA'}, True, id="simple name match"),
            pytest.param({'name': 'AAA'}, {'name': 'BBB'}, False, id="simple name mismatch"),
            # at least one matching ID is required
            pytest.param(
                {'name': 'AAA', 'isbn': '978-3-16-148410-0'},
                {'name': 'AAA'},
                False,
                id="incoming has no matching ID",
            ),
            pytest.param(
                {'name': 'AAA', 'isbn': '978-3-16-148410-0'},
                {'name': 'AAA', 'isbn': '978-3-16-148410-0'},
                True,
                id="matching name and isbn",
            ),
            # one matching ID should be enough
            pytest.param(
                {'name': 'AAA', 'isbn': '978-3-16-148410-0'},
                {'name': 'AAA', 'isbn': '978-3-16-148410-0', 'doi': 'xxx'},
                True,
                id="matching name and isbn with extra id",
            ),
            pytest.param(
                {'name': 'AAA', 'isbn': '978-3-16-148410-0', 'doi': 'xxx'},
                {'name': 'AAA', 'isbn': '978-3-16-148410-0', 'issn': '1111-2222'},
                True,
                id="matching name and isbn with extra id on both sides",
            ),
            # no mismatch between IDs is allowed
            pytest.param(
                {'name': 'AAA', 'isbn': '978-3-16-148410-0', 'doi': 'xxx'},
                {'name': 'AAA', 'isbn': '978-3-16-148410-0', 'doi': 'yyy'},
                False,
                id="clashing ids even though the rest matches",
            ),
            # proprietary IDs may also serve for matching
            pytest.param(
                {'name': 'AAA', 'proprietary_ids': ['XXX']},
                {'name': 'AAA', 'proprietary_ids': ['XXX']},
                True,
                id="match based on proprietary id",
            ),
            pytest.param(
                {'name': 'AAA', 'isbn': '978-3-16-148410-0', 'proprietary_ids': ['XXX']},
                {'name': 'AAA', 'proprietary_ids': ['XXX']},
                True,
                id="march on proprietary id with extra id on one side",
            ),
            # mismatching proprietary IDs are no problem if other ids match
            pytest.param(
                {'name': 'AAA', 'isbn': '978-3-16-148410-0', 'proprietary_ids': ['XXX']},
                {'name': 'AAA', 'isbn': '978-3-16-148410-0', 'proprietary_ids': ['YYY']},
                True,
                id="matching name and id with mismatch in proprietary ids",
            ),
            # matching proprietary IDs do not "save it" when other IDs mismatch
            pytest.param(
                {'name': 'AAA', 'isbn': '978-3-16-148410-0', 'proprietary_ids': ['XXX']},
                {'name': 'AAA', 'isbn': '978-1-4028-9462-6', 'proprietary_ids': ['XXX']},
                False,
                id="matching name and proprietary id with mismatch in other id",
            ),
            # uri merge - one way
            pytest.param(
                {'name': 'AAA', 'isbn': '978-3-16-148410-0'},
                {'name': 'AAA', 'isbn': '978-3-16-148410-0', 'uri': 'https://aaa.bb/'},
                True,
                id="one way uri merge",
            ),
            # uri merge - two way
            pytest.param(
                {'name': 'AAA', 'isbn': '978-3-16-148410-0', 'uri': 'https://bbb.aa/'},
                {'name': 'AAA', 'isbn': '978-3-16-148410-0', 'uri': 'https://aaa.bb/'},
                True,
                id="two way uri merge",
            ),
            # pub_type upgrade
            pytest.param(
                {'name': 'AAA', 'isbn': '978-3-16-148410-0', 'pub_type': Title.PUB_TYPE_UNKNOWN},
                {'name': 'AAA', 'isbn': '978-3-16-148410-0', 'pub_type': Title.PUB_TYPE_BOOK},
                True,
                id="pub_type upgrade",
            ),
            # pub_type upgrade
            pytest.param(
                {'name': 'AAA', 'isbn': '978-3-16-148410-0', 'pub_type': Title.PUB_TYPE_JOURNAL},
                {'name': 'AAA', 'isbn': '978-3-16-148410-0', 'pub_type': Title.PUB_TYPE_BOOK},
                True,
                id="pub_type upgrade",
            ),
            # isbn normalization
            pytest.param(
                {'name': 'AAA', 'isbn': '978-3-16-148410-0'},
                {'name': 'AAA', 'isbn': '9783161484100'},
                True,
                id="isbn normalization",
            ),
            # title normalization
            pytest.param(
                {'name': 'AAA  BBB', 'isbn': '978-3-16-148410-0'},
                {'name': 'AAA BBB', 'isbn': '978-3-16-148410-0'},
                True,
                id="title normalization",
            ),
            # case insensitive merging
            pytest.param(
                {'name': 'NATURE', 'isbn': '978-3-16-148410-0'},
                {'name': 'Nature', 'isbn': '978-3-16-148410-0'},
                True,
                id="case insensitive title",
            ),
        ],
    )
    def test_get_or_create_merging_strategy(
        self, db_title: dict, in_title: dict, merge: bool, reverse: bool
    ):
        if reverse:
            # switch db_title <-> in_title because the result should not depend on the order
            # of imports, so we get some extra testing for free and do not need to create
            # reversed tests manually
            db_title, in_title = in_title, db_title
        # prepare the db_title in the database as if it were imported before
        db_title = dict(db_title)  # create copy not to change it for the following run if modified
        # the following would normally happen on first import of the title
        db_title['name'] = normalize_title(db_title['name'])
        if 'uri' in db_title:
            # uri is stored in an array, so we need to wrap it here
            db_uri = db_title.pop('uri')
            db_title['uris'] = [db_uri]
        if 'isbn' in db_title:
            # this would normally happen on first import of the title
            db_title['isbn'] = normalize_isbn(db_title['isbn'])
        Title.objects.create(**db_title)
        assert Title.objects.count() == 1
        # now process the in_title
        title_rec = TitleRec(**in_title)
        assert type(title_rec.proprietary_ids) is set
        tm = TitleManager()
        # the following is necessary because normalization would normally be carried out
        # in `counter_record_to_title_rec` which we do not use here
        title_rec = tm.normalize_title_rec(title_rec)
        tm.prefetch_titles([title_rec])
        tm.get_or_create(title_rec)
        if merge:
            assert Title.objects.count() == 1, 'titles should be merged'
            # compare all different IDs and check they were merged from both records
            title = Title.objects.get()
            for id_attr in 'isbn', 'issn', 'eissn', 'doi':
                # id_attrs should be merged
                exp_value = db_title.get(id_attr, '') or in_title.get(id_attr, '')
                if id_attr == 'isbn':
                    exp_value = normalize_isbn(exp_value)
                assert (
                    getattr(title, id_attr) == exp_value
                ), f'{id_attr} is DB should be "{exp_value}"'
            assert set(title.proprietary_ids) == set(db_title.get('proprietary_ids', '')) | set(
                in_title.get('proprietary_ids', [])
            )
            assert set(title.uris) == set(
                filter(None, [*db_title.get('uris', []), in_title.get('uri')])
            )
            db_pub_type = db_title.get('pub_type', Title.PUB_TYPE_UNKNOWN)
            in_pub_type = in_title.get('pub_type', Title.PUB_TYPE_UNKNOWN)
            if db_pub_type != Title.PUB_TYPE_UNKNOWN:
                assert title.pub_type == db_pub_type, 'DB pub_type should be preserved'
            elif in_pub_type != Title.PUB_TYPE_UNKNOWN:
                assert title.pub_type == in_pub_type, 'Incoming pub_type should be used'
            else:
                assert title.pub_type == Title.PUB_TYPE_UNKNOWN, 'pub_type should be unknown'
            # check that when reimporting the same in_record that it does not hit database again
            # (this checks that the pre-fetched data in TitleManager are properly updated on merge)
            tm.stats = Counter()
            tm.get_or_create(title_rec)
            assert tm.stats['existing'] == 1, 'the reimported title should be there in full'
        else:
            assert Title.objects.count() == 2, 'titles should not be merged'

    def test_get_or_create(self):
        """
        Creating same title
        """
        tm = TitleManager()
        record = TitleRec(name='TITLE', pub_type=Title.PUB_TYPE_BOOK, isbn='977-481-83-13d6-2')

        # creating same title
        pk1 = tm.get_or_create(record)
        assert tm.stats['created'] == 1
        assert tm.stats['existing'] == 0
        pk2 = tm.get_or_create(record)
        assert tm.stats['created'] == 1
        assert tm.stats['existing'] == 1
        assert pk1 is not None
        assert pk2 is not None
        assert pk1 == pk2

    def test_get_or_create_with_two_winners(self):
        """
        Test a real-world situation where there are two matching candidates in the DB.

        The challenge here is that if we pick the wrong one and then 'upgrade it' using the
        data from the incoming data, it would start clashing with the other record, which we
        need to avoid.
        """
        t1 = Title.objects.create(name='A', issn='1111-2222')
        t2 = Title.objects.create(name='A', issn='1111-2222', eissn='2222-1111')

        tm = TitleManager()
        record = TitleRec(name='A', issn='1111-2222', eissn='2222-1111')
        tm.prefetch_titles([record])
        pk = tm.get_or_create(record)
        assert tm.stats['existing'] == 1, "find existing, not upgrade other if we don't have to"
        assert pk == t2.pk

    def test_get_or_create_with_three_winners(self):
        """
        Test a real-world situation where there are two matching candidates in the DB.

        The challenge here is that if we pick the wrong one and then 'upgrade it' using the
        data from the incoming data, it would start clashing with the other record, which we
        need to avoid.
        """
        t1 = Title.objects.create(name='A', issn='1111-2222')
        t2 = Title.objects.create(name='A', issn='1111-2222', eissn='2222-1111')
        t3 = Title.objects.create(name='A', issn='1111-2222', eissn='2222-1111', doi='https://x/')

        tm = TitleManager()
        record = TitleRec(name='A', issn='1111-2222', eissn='2222-1111')
        tm.prefetch_titles([record])
        pk = tm.get_or_create(record)
        assert tm.stats['existing'] == 1, "find existing, not upgrade other if we don't have to"
        assert pk == t3.pk

    @pytest.mark.parametrize(
        ['ids', 'attrs'],
        [
            ({'Print_ISSN': '1111-2222'}, {'issn': '1111-2222'}),
            (
                {'Print_ISSN': '1111-2222', 'Proprietary': 'FOO'},
                {'issn': '1111-2222', 'proprietary_ids': {'FOO'}},
            ),
            # test normalization as well
            (
                {'Print_ISSN': '1111- 2222 ', 'Proprietary': ' FOO ', 'ISBN': '978-3-16-148410-0'},
                {'issn': '1111-2222', 'proprietary_ids': {'FOO'}, 'isbn': '9783161484100'},
            ),
            # garbage in ISBN
            (
                {
                    'Print_ISSN': '1111- 2222 ',
                    'Proprietary': ' FOO ',
                    'ISBN': '978-3-16-148410-0 (print); 978-3-16-148411-1 (ebook)',
                },
                {'issn': '1111-2222', 'proprietary_ids': {'FOO'}, 'isbn': '9783161484100'},
            ),
            # garbage in ISSN
            (
                {'Print_ISSN': '1111- 2222 (print)', 'Proprietary': ' FOO ',},
                {'issn': '1111-2222', 'proprietary_ids': {'FOO'}},
            ),
            (
                {'Print_ISSN': 'garbage 1111-2222', 'Proprietary': ' FOO ',},
                {'issn': '1111-2222', 'proprietary_ids': {'FOO'}},
            ),
            (
                {'Print_ISSN': 'garbagegarbage', 'Proprietary': ' FOO ',},
                {'issn': 'garbagega', 'proprietary_ids': {'FOO'}},
            ),
        ],
    )
    def test_counter_record_to_title_rec(self, ids, attrs):
        cr = CounterRecordFactory.create(title_ids=ids)
        tm = TitleManager()
        title_rec = tm.counter_record_to_title_rec(cr)
        for key, value in attrs.items():
            assert getattr(title_rec, key) == value
        for key in ['issn', 'eissn', 'isbn', 'doi', 'proprietary_ids', 'uri']:
            if key not in attrs:
                assert not getattr(title_rec, key), 'unset attribute should be empty'
