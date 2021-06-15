import pytest
from django.db.models import Count

from logs.logic.data_import import TitleManager, TitleRec
from publications.models import Title


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
