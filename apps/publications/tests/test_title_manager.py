import pytest

from logs.logic.data_import import TitleManager, TitleRec
from publications.models import Title


@pytest.mark.django_db
class TestTitleManager(object):
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
