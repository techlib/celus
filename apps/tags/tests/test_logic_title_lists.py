from io import StringIO

import pytest
from publications.fake_data import TitleFactory

from tags.logic.titles_lists import CsvTitleListReader


@pytest.mark.django_db
class TestCsvTitleListReader:
    def test_column_name_parsing(self):
        reader = CsvTitleListReader()
        with open('test-data/tagging_batch/plain-title-list.csv', 'r') as infile:
            # we just need parsing of the column names, so we do just one iteration
            next(reader.parse_data(infile))
            assert reader.column_names == {
                'isbn': 'ISBN',
                'issn': 'issn',
                'eissn': 'eISSN',
            }, 'column names are correctly extracted from data'

    def test_record_generation(self):
        reader = CsvTitleListReader()
        with open('test-data/tagging_batch/plain-title-list.csv', 'r') as infile:
            data = list(reader.parse_data(infile))
        assert len(data) == 6
        assert data[0].title_rec.isbn == '9780787960186'
        assert data[0].tag_names == []

    @pytest.mark.parametrize(
        ['batch_size', 'num_queries'], [(1, 6), (2, 3), (6, 1), (10, 1), (1000, 1)]
    )
    @pytest.mark.parametrize(
        ['merge_issns', 'expected_counts'],
        [(False, [1, 1, 0, 0, 0, 0]), (True, [1, 1, 0, 0, 1, 0])],
    )
    def test_title_matching(
        self, merge_issns, expected_counts, batch_size, num_queries, django_assert_num_queries
    ):
        TitleFactory.create(isbn='9780787960186')
        TitleFactory.create(issn='1234-5678')
        reader = CsvTitleListReader()
        with open('test-data/tagging_batch/plain-title-list.csv', 'r') as infile:
            with django_assert_num_queries(num_queries):
                data = list(
                    reader.process_source(infile, merge_issns=merge_issns, batch_size=batch_size)
                )
        assert len(data) == 6
        assert [len(rec.title_ids) for rec in data] == expected_counts

    def test_explicit_tags_extraction(self):
        reader = CsvTitleListReader(tag_name_column='tag')
        with open('test-data/tagging_batch/plain-title-list-with-tags.csv', 'r') as infile:
            data = list(reader.parse_data(infile))
        assert len(data) == 7
        assert data[0].title_rec.isbn == '9780787960186'
        assert data[0].tag_names == ['prase']

    @pytest.mark.parametrize(
        'tag_col', ['tag', 'tag ', ' TAG', ' tAg\t', 'TaG\n', 'TAG\r\n', '\ntag']
    )
    def test_explicit_tags_extraction_with_mangled_col_name(self, tag_col):
        infile = StringIO(f'ISSN,"{tag_col}"\n1234-5678,prase')
        reader = CsvTitleListReader(tag_name_column='tag')
        infile.seek(0)
        data = list(reader.parse_data(infile))
        assert len(data) == 1
        assert data[0].title_rec.issn == '1234-5678'
        assert data[0].tag_names == ['prase']

    def test_explicit_tags_extraction_nonexistent_col_name(self):
        infile = StringIO('ISSN,tags\n1234-5678,prase')
        infile.seek(0)
        reader = CsvTitleListReader(tag_name_column='tag')
        with pytest.raises(ValueError):
            list(reader.parse_data(infile))
