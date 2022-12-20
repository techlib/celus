from pathlib import Path
from unittest.mock import patch

import pytest
from celus_nigiri.counter4 import Counter4BR2Report
from celus_nigiri.counter5 import Counter5TableReport, Counter5TRReport
from django.db.models import Count, Sum
from django.urls import reverse
from logs.models import AccessLog, DimensionText, ImportBatch
from organizations.tests.conftest import organization_random, organizations  # noqa - fixture
from publications.models import PlatformTitle, Title

from test_fixtures.entities.logs import ManualDataUploadFullFactory

from ..exceptions import DataStructureError
from ..logic.data_import import import_counter_records


@pytest.mark.django_db
class TestDataImport:

    """
    Tests functionality of the logic.data_import module
    """

    def test_import_counter_records_simple_data_0d(
        self, counter_records_0d, organizations, report_type_nd, platform
    ):
        assert AccessLog.objects.count() == 0
        assert Title.objects.count() == 0
        report_type = report_type_nd(0)
        import_counter_records(report_type, organizations[0], platform, counter_records_0d)
        assert AccessLog.objects.count() == 1
        assert ImportBatch.objects.count() == 1
        assert Title.objects.count() == 1
        al = AccessLog.objects.get()
        assert al.value == 50
        assert al.dim1 is None
        assert PlatformTitle.objects.count() == 1

    def test_import_counter_records_simple_data_0d_more_passes(
        self, counter_records_nd, organizations, report_type_nd, platform
    ):
        """
        Tests that when the import has to go over the imported data in several passes
        (batches, not import batches), it still functions properly
        """
        assert AccessLog.objects.count() == 0
        record_number = 10
        crs = list(counter_records_nd(1, record_number=record_number))
        report_type = report_type_nd(1)
        import_counter_records(report_type, organizations[0], platform, crs, buffer_size=1)
        assert AccessLog.objects.count() == record_number

    def test_simple_data_import_1d(
        self, counter_records_nd, organizations, report_type_nd, platform
    ):
        assert AccessLog.objects.count() == 0
        assert Title.objects.count() == 0
        crs = list(counter_records_nd(1))
        report_type = report_type_nd(1)
        import_counter_records(report_type, organizations[0], platform, crs)
        assert AccessLog.objects.count() == 1
        assert Title.objects.count() == 1
        al = AccessLog.objects.get()
        assert al.value == crs[0].value
        # check that the remap of the value is the same as the original text value
        assert DimensionText.objects.get(pk=al.dim1).text == crs[0].dimension_data['dim0']
        assert al.dim2 is None

    def test_data_import_mutli_3d(
        self, counter_records_nd, organizations, report_type_nd, platform
    ):
        assert AccessLog.objects.count() == 0
        assert Title.objects.count() == 0
        crs = list(counter_records_nd(3, record_number=10))
        report_type = report_type_nd(3)
        _ibs, stats = import_counter_records(report_type, organizations[0], platform, crs)
        assert stats['skipped logs'] == 0
        assert stats['new logs'] == 10
        assert AccessLog.objects.count() == 10
        assert Title.objects.count() > 0
        al = AccessLog.objects.order_by('pk')[0]
        assert al.value == crs[0].value
        # check that the remap of the value is the same as the original text value
        assert DimensionText.objects.get(pk=al.dim1).text == crs[0].dimension_data['dim0']
        assert DimensionText.objects.get(pk=al.dim2).text == crs[0].dimension_data['dim1']
        assert DimensionText.objects.get(pk=al.dim3).text == crs[0].dimension_data['dim2']
        assert al.dim4 is None

    @pytest.mark.parametrize(
        ['months', 'log_count', 'log_sum'],
        [
            (None, 6, 63),
            (['2018-01-01'], 3, 7),
            (['2018-01-01', '2018-03-01'], 4, 39),
            (['2018-01-01', '2018-02-01'], 5, 31),
            (['2018-01-01', '2018-02-01', '2018-03-01'], 6, 63),
            (['2018-02-01', '2018-03-01'], 3, 56),
            (['2018-02-01'], 2, 24),
        ],
    )
    def test_data_import_month_skipping(
        self, counter_records, organizations, report_type_nd, platform, months, log_count, log_sum
    ):
        assert AccessLog.objects.count() == 0
        assert Title.objects.count() == 0
        data = [
            [None, '2018-01-01', '1v1', '2v1', '3v1', 1],
            [None, '2018-01-01', '1v2', '2v1', '3v1', 2],
            [None, '2018-01-01', '1v2', '2v2', '3v1', 4],
            [None, '2018-02-01', '1v1', '2v1', '3v1', 8],
            [None, '2018-02-01', '1v1', '2v2', '3v2', 16],
            [None, '2018-03-01', '1v1', '2v3', '3v2', 32],
        ]
        crs = list(counter_records(data, metric='Hits', platform=platform.name))
        organization = organizations[0]
        report_type = report_type_nd(3)
        import_counter_records(report_type, organization, platform, crs, months=months)
        assert AccessLog.objects.count() == log_count
        assert AccessLog.objects.aggregate(sum=Sum('value'))['sum'] == log_sum

    def test_data_import_mutli_3d_repeating_data(
        self, counter_records_nd, organizations, report_type_nd, platform
    ):
        """
        Tests that when the same values occur in the import data, they are remapped correctly to
        the save database value.
        """
        assert AccessLog.objects.count() == 0
        assert Title.objects.count() == 0
        crs = list(
            counter_records_nd(3, record_number=10, title='Title ABC', dim_value='one value')
        )
        rt = report_type_nd(3)  # type: ReportType
        import_counter_records(rt, organizations[0], platform, crs)
        assert AccessLog.objects.count() == 10
        assert Title.objects.count() > 0
        al1, al2 = AccessLog.objects.order_by('pk')[:2]
        assert al1.value == crs[0].value
        # check that only one remap is created for each dimension
        assert DimensionText.objects.filter(text='one value').count() == 3
        dt1 = DimensionText.objects.get(text='one value', dimension=rt.dimensions_sorted[0])
        # check that values with the same dimension use the same remap
        assert al1.dim1 == dt1.pk
        assert al2.dim1 == dt1.pk
        dt2 = DimensionText.objects.get(text='one value', dimension=rt.dimensions_sorted[1])
        assert al1.dim2 == dt2.pk
        assert al2.dim2 == dt2.pk
        assert al1.dim3 is not None
        assert al1.dim4 is None

    def test_reimport(self, counter_records_nd, organizations, report_type_nd, platform):
        """
        Test that reimporting the same data will lead to an exception
        """
        crs = list(counter_records_nd(3, record_number=1, title='Title ABC', dim_value='one value'))
        rt = report_type_nd(3)  # type: ReportType
        _ibs, stats = import_counter_records(rt, organizations[0], platform, crs)
        assert AccessLog.objects.count() == 1
        assert Title.objects.count() == 1
        assert stats['new logs'] == 1
        assert stats['new platformtitles'] == 1
        with pytest.raises(DataStructureError):
            import_counter_records(rt, organizations[0], platform, crs)

    @pytest.mark.parametrize(['buffer_size'], [(10,), (3,), (2,), (1,)])
    def test_duplicated_data_in_one_import(
        self, counter_records_nd, organizations, report_type_nd, platform, buffer_size
    ):
        """
        Test that when there are several records with the same dimensions in the records,
        they are properly merged together.
        It should work regardless of buffer_size - which means even if the clashing records
        are in different batches
        """
        cr = list(counter_records_nd(3, record_number=1, title='Title ABC', dim_value='one'))[0]
        crs = [cr, cr, cr]
        rt = report_type_nd(3)  # type: ReportType
        _ibs, stats = import_counter_records(
            rt, organizations[0], platform, crs, buffer_size=buffer_size
        )
        assert AccessLog.objects.count() == 1
        assert AccessLog.objects.get().value == 3 * cr.value
        assert Title.objects.count() == 1
        assert stats['new logs'] == 1
        assert stats['new platformtitles'] == 1


@pytest.mark.django_db
class TestCounter4Import:
    def test_import_br2_tsv(self, organizations, report_type_nd, platform):
        rt = report_type_nd(1, dimension_names=['Publisher'])
        from pycounter import report

        data = report.parse(str(Path(__file__).parent / 'data/counter4/counter4_br2.tsv'))
        reader = Counter4BR2Report()
        records = [e for e in reader.read_report(data)]
        assert len(records) == 60  # 12 months, 5 titles
        organization = organizations[0]
        assert AccessLog.objects.count() == 0
        _ibs, stats = import_counter_records(rt, organization, platform, (e for e in records))
        assert AccessLog.objects.count() == 60
        assert stats['new logs'] == 60
        values = [
            al['value']
            for al in AccessLog.objects.filter(
                target__name='Columbia Electronic Encyclopedia, 6th Edition'
            )
            .order_by('date')
            .values()
        ]
        assert len(values) == 12
        assert values == [1, 10, 2, 3, 5, 0, 0, 0, 0, 0, 0, 0]

    def test_c4_import_title_types_ids_and_platform(self, organizations, report_type_nd, platform):
        expected = [
            (
                "Auditing Your Human Resources Department: A Step-by-Step Guide to Assessing the "
                "Key Areas of Your Program",
                ['453619'],
                '9780814416617',
            ),
            ("Columbia Electronic Encyclopedia, 6th Edition", ['576175'], '9780787650155'),
            ("International Business Times", [], ''),
            ("World Congress on Engineering 2007 (Volume 1)", ['422959'], '9789889867157'),
            ("World Congress on Engineering 2009 (Volume 1)", ['657512'], '9789881701251'),
        ]

        reader = Counter4BR2Report()
        rt = report_type_nd(len(reader.dimensions), dimension_names=reader.dimensions)

        from pycounter import report

        data = report.parse(str(Path(__file__).parent / 'data/counter4/counter4_br2.tsv'))

        records = [e for e in reader.read_report(data)]
        assert len(records) == 60  # 12 months, 5 titles
        organization = organizations[0]
        assert Title.objects.count() == 0
        import_counter_records(rt, organization, platform, (e for e in records))
        assert Title.objects.count() == 5
        # test title publication type
        assert list(
            Title.objects.order_by('pub_type').values('pub_type').annotate(count=Count('id'))
        ) == [
            {'pub_type': Title.PUB_TYPE_BOOK, 'count': 4},
            {'pub_type': Title.PUB_TYPE_UNKNOWN, 'count': 1},
        ]
        # test other title properties
        for title in Title.objects.all():
            for exp_title, exp_ids, exp_isbn in expected:
                if exp_title == title.name:
                    assert title.proprietary_ids == exp_ids
                    assert title.isbn == exp_isbn
                    break
            else:
                assert False, 'expected title was not found'
        # test that the Platform dimension was properly handled
        pl_attr = rt.dim_name_to_dim_attr('Platform')
        pl_dim = rt.dimension_by_attr_name(pl_attr)
        ebsco_text = DimensionText.objects.filter(dimension=pl_dim, text='EBSCOhost')
        assert ebsco_text.exists(), 'corresponding DimensionText should have been created'
        ebsco_text = ebsco_text.get()
        for al in AccessLog.objects.all():
            assert getattr(al, pl_attr) == ebsco_text.pk


@pytest.mark.django_db
class TestCounter5Import:
    @pytest.mark.parametrize(
        ['filename', 'expected'],
        [
            ('counter5_table_dr.csv', [("ARTICLES", ['Test123'], []), ("BOOKS", ['Test456'], [])]),
            (
                'COUNTER_R5_Report_Examples_TR.csv',
                [("Journal Six", ['xyz123'], ['https://foo.bar.baz/'])],
            ),
        ],
    )
    def test_c5_import_title_types_and_ids(
        self, organization_random, report_type_nd, platform, filename, expected
    ):
        # we do not care much about the dimensions - just about titles
        rt = report_type_nd(0)

        reader = Counter5TableReport()
        records = reader.file_to_records(str(Path(__file__).parent / 'data/counter5' / filename))
        assert Title.objects.count() == 0
        import_counter_records(rt, organization_random, platform, records)
        assert Title.objects.count() == len(expected)
        for title in Title.objects.all():
            for exp_title, exp_ids, exp_uris in expected:
                if exp_title == title.name:
                    assert title.proprietary_ids == exp_ids
                    assert title.uris == exp_uris
                    break
            else:

                assert False, 'expected title was not found'

    @pytest.mark.parametrize(
        ['filename', 'count'],
        [
            ('counter5_table_dr.csv', 121),
            ('counter5_table_dr.tsv', 121),
            ('counter5_table_ir_m1.csv', 22788),
            ('counter5_table_pr.csv', 252),
        ],
    )
    def test_c5_table_record_count(self, filename, count):
        reader = Counter5TableReport()
        records = reader.file_to_records(str(Path(__file__).parent / 'data/counter5' / filename))
        assert count == len(list(records))

    def test_c5_tr_nature_merging(self, organization_random, report_type_nd, platform):
        # we do not care much about the dimensions - just about titles
        rt = report_type_nd(0)

        reader = Counter5TRReport()
        records = reader.file_to_records(
            str(Path(__file__).parent / 'data/counter5/counter5_tr_nature.json')
        )
        import_counter_records(rt, organization_random, platform, records)
        assert Title.objects.filter(name='Nature').count() == 1, 'only one Nature'


@pytest.mark.django_db
class TestReprocessMDU:
    def test_reimport_admin_action(self, admin_client):
        mdu = ManualDataUploadFullFactory.create()
        # reprocess and check
        with patch('logs.admin.import_manual_upload_data') as task_patch:
            admin_client.post(
                reverse('admin:logs_manualdataupload_changelist'),
                {'action': 'reimport', '_selected_action': [str(mdu.pk)]},
            )
            task_patch.apply_async.assert_called_once()
