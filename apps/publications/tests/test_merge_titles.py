import pytest
from django.core.management import call_command
from hcube.api.models.aggregation import Sum as HSum

from logs.cubes import ch_backend, AccessLogCube
from logs.models import AccessLog
from publications.logic.title_management import find_mergeable_titles, merge_titles
from publications.models import Title, PlatformTitle
from test_fixtures.entities.logs import ImportBatchFullFactory


@pytest.fixture()
def natures():
    t1 = Title(name='Nature', pub_type=Title.PUB_TYPE_JOURNAL, proprietary_ids=['SN:41586'])
    t2 = Title(
        name='Nature',
        pub_type=Title.PUB_TYPE_JOURNAL,
        issn='0028-0836',
        eissn='1476-4687',
        doi='10.1038/41586.1476-4687',
        proprietary_ids=['EBSCOhost:KBID:50974', 'ProQuest:40569', 'SN:41586', 'gale:0359'],
    )
    t3 = Title(
        name='Nature',
        pub_type=Title.PUB_TYPE_BOOK,
        isbn='9780691127934',
        proprietary_ids=['JSTOR:10.2307/j.ctt7rmgd'],
    )
    Title.objects.bulk_create([t1, t2, t3])
    return [t1, t2, t3]


@pytest.fixture()
def mlas():
    """
    The most massive group of possibly matching titles
    """
    spec = [
        ('MLA International Bibliography', 'B', '', '', '', '', ['EBSCOhost:mzh']),
        ('MLA International Bibliography', 'B', '', '', '9780807128237', '', []),
        ('MLA International Bibliography', 'B', '', '', '9781107057258', '', []),
        ('MLA International Bibliography', 'B', '', '', '9783039112364', '', []),
        ('MLA International Bibliography', 'B', '', '', '9780806129709', '', []),
        ('MLA International Bibliography', 'B', '', '', '9780521810562', '', []),
        ('MLA International Bibliography', 'B', '', '', '9781906155049', '', []),
        ('MLA International Bibliography', 'B', '', '', '9781567186000', '', []),
        ('MLA International Bibliography', 'B', '', '', '9780231186254', '', []),
        ('MLA International Bibliography', 'B', '', '', '9781847181824', '', []),
        ('MLA International Bibliography', 'B', '', '', '9781570035524', '', []),
        ('MLA International Bibliography', 'B', '', '', '9781843840305', '', []),
        ('MLA International Bibliography', 'B', '', '', '9780870133831', '', []),
        ('MLA International Bibliography', 'B', '', '', '9780415044479', '', []),
        ('MLA International Bibliography', 'B', '', '', '9781572304017', '', []),
        ('MLA International Bibliography', 'B', '', '', '9780826210586', '', []),
        ('MLA International Bibliography', 'B', '', '', '9780816650460', '', []),
        ('MLA International Bibliography', 'B', '', '', '9781608870523', '', []),
        ('MLA International Bibliography', 'B', '', '', '9781559341806', '', []),
        ('MLA International Bibliography', 'B', '', '', '9780847700905', '', []),
        ('MLA International Bibliography', 'B', '', '', '9780521383080', '', []),
        ('MLA International Bibliography', 'B', '', '', '9780812235647', '', []),
        ('MLA International Bibliography', 'O', '0887-4409', '0887-4409', '', '', []),
        ('MLA International Bibliography', 'O', '0730-6857', '0730-6857', '', '', []),
        ('MLA International Bibliography', 'O', '0073-0513', '0073-0513', '', '', []),
        ('MLA International Bibliography', 'O', '1135-0504', '1135-0504', '', '', []),
        ('MLA International Bibliography', 'O', '1056-3970', '1056-3970', '', '', []),
        ('MLA International Bibliography', 'O', '1436-7521', '1436-7521', '', '', []),
        ('MLA International Bibliography', 'O', '0946-0349', '0946-0349', '', '', []),
        ('MLA International Bibliography', 'O', '0308-7662', '0308-7662', '', '', []),
        ('MLA International Bibliography', 'O', '0143-1064', '0143-1064', '', '', []),
        ('MLA International Bibliography', 'O', '1045-6619', '1045-6619', '', '', []),
        ('MLA International Bibliography', 'O', '0454-8132', '0454-8132', '', '', []),
        ('MLA International Bibliography', 'O', '0278-310X', '0278-310X', '', '', []),
        ('MLA International Bibliography', 'O', '0893-5963', '0893-5963', '', '', []),
        ('MLA International Bibliography', 'O', '0028-3983', '0028-3983', '', '', []),
        ('MLA International Bibliography', 'O', '1611-258X', '1611-258X', '', '', []),
        ('MLA International Bibliography', 'O', '2629-7094', '2629-7094', '', '', []),
        ('MLA International Bibliography', 'O', '2364-4311', '2364-4311', '', '', []),
        ('MLA International Bibliography', 'O', '2465-8545', '2465-8545', '', '', []),
        ('MLA International Bibliography', 'O', '2211-5846', '2211-5846', '', '', []),
        ('MLA International Bibliography', 'O', '1612-8427', '1612-8427', '', '', []),
        ('MLA International Bibliography', 'O', '1054-058X', '1054-058X', '', '', []),
        ('MLA International Bibliography', 'O', '0929-6999', '0929-6999', '', '', []),
        ('MLA International Bibliography', 'O', '0194-035X', '0194-035X', '', '', []),
        ('MLA International Bibliography', 'O', '1053-9344', '1053-9344', '', '', []),
        ('MLA International Bibliography', 'O', '2065-3867', '2065-3867', '', '', []),
        ('MLA International Bibliography', 'O', '1531-3964', '1531-3964', '', '', []),
        ('MLA International Bibliography', 'O', '1479-9308', '1479-9308', '', '', []),
        ('MLA International Bibliography', 'O', '0255-2779', '0255-2779', '', '', []),
        ('MLA International Bibliography', 'O', '1571-4934', '1571-4934', '', '', []),
        ('MLA International Bibliography', 'O', '1204-4725', '1204-4725', '', '', []),
        ('MLA International Bibliography', 'O', '0738-1409', '0738-1409', '', '', []),
        ('MLA International Bibliography', 'O', '0731-8200', '0731-8200', '', '', []),
        ('MLA International Bibliography', 'O', '0553-4895', '0553-4895', '', '', []),
        ('MLA International Bibliography', 'O', '0430-7690', '0430-7690', '', '', []),
        ('MLA International Bibliography', 'O', '0250-0035', '0250-0035', '', '', []),
        ('MLA International Bibliography', 'O', '0046-0842', '0046-0842', '', '', []),
        ('MLA International Bibliography', 'O', '0533-2869', '0533-2869', '', '', []),
        ('MLA International Bibliography', 'O', '0576-8233', '0576-8233', '', '', []),
        ('MLA International Bibliography', 'O', '0544-4713', '0544-4713', '', '', []),
        ('MLA International Bibliography', 'O', '0458-7359', '0458-7359', '', '', []),
        ('MLA International Bibliography', 'O', '0083-4823', '0083-4823', '', '', []),
        ('MLA International Bibliography', 'O', '0022-0868', '0022-0868', '', '', []),
        ('MLA International Bibliography', 'O', '0286-3855', '0286-3855', '', '', []),
        ('MLA International Bibliography', 'O', '1962-1329', '1962-1329', '', '', []),
        ('MLA International Bibliography', 'O', '0893-8288', '0893-8288', '', '', []),
        ('MLA International Bibliography', 'O', '0047-6161', '0047-6161', '', '', []),
        ('MLA International Bibliography', 'O', '0169-9563', '0169-9563', '', '', []),
        ('MLA International Bibliography', 'O', '0163-8246', '0163-8246', '', '', []),
        ('MLA International Bibliography', 'O', '0081-752X', '0081-752X', '', '', []),
        ('MLA International Bibliography', 'O', '0071-5654', '0071-5654', '', '', []),
        ('MLA International Bibliography', 'O', '2211-1018', '2211-1018', '', '', []),
        ('MLA International Bibliography', 'O', '0261-9814', '0261-9814', '', '', []),
        ('MLA International Bibliography', 'O', '2158-415X', '2158-415X', '', '', []),
        ('MLA International Bibliography', 'O', '0277-3384', '0277-3384', '', '', []),
        ('MLA International Bibliography', 'O', '1376-3199', '1376-3199', '', '', []),
        ('MLA International Bibliography', 'O', '1066-4971', '1066-4971', '', '', []),
        ('MLA International Bibliography', 'O', '1864-3396', '1864-3396', '', '', []),
        ('MLA International Bibliography', 'O', '8755-4208', '8755-4208', '', '', []),
        ('MLA International Bibliography', 'O', '1555-7065', '1555-7065', '', '', []),
        ('MLA International Bibliography', 'O', '2397-2947', '2397-2947', '', '', []),
        ('MLA International Bibliography', 'O', '0260-8480', '0260-8480', '', '', []),
        ('MLA International Bibliography', 'O', '0015-5896', '0015-5896', '', '', []),
        ('MLA International Bibliography', 'O', '0047-276X', '0047-276X', '', '', []),
        ('MLA International Bibliography', 'O', '1298-4655', '1298-4655', '', '', []),
        ('MLA International Bibliography', 'O', '0882-486X', '0882-486X', '', '', []),
        ('MLA International Bibliography', 'O', '1424-8689', '1424-8689', '', '', []),
        ('MLA International Bibliography', 'O', '0970-8332', '0970-8332', '', '', []),
        ('MLA International Bibliography', 'O', '2578-4021', '2578-4021', '', '', []),
        ('MLA International Bibliography', 'O', '1287-7484', '1287-7484', '', '', []),
        ('MLA International Bibliography', 'O', '1079-2554', '1079-2554', '', '', []),
        ('MLA International Bibliography', 'O', '1073-9637', '1073-9637', '', '', []),
        ('MLA International Bibliography', 'O', '0888-3904', '0888-3904', '', '', []),
    ]
    return Title.objects.bulk_create(
        [
            Title(
                name=name,
                pub_type=pub_type,
                issn=issn,
                eissn=eissn,
                isbn=isbn,
                doi=doi,
                proprietary_ids=proprietary_ids,
            )
            for (name, pub_type, issn, eissn, isbn, doi, proprietary_ids) in spec
        ]
    )


@pytest.fixture()
def matching_10():
    """
    10 matching titles
    """
    spec = [
        ('Foo', 'B', '', '', '', '', ['EBSCOhost:mzh']),
        ('Foo', 'B', '', '', '9780807128237', '', []),
        ('Foo', 'B', '', '', '9780807128237', '', ['xyz']),
        ('Foo', 'O', '0887-4409', '0887-4409', '9780807128237', '', []),
        ('Foo', 'O', '0887-4409', '', '9780807128237', '', []),
        ('Foo', 'O', '', '0887-4409', '9780807128237', '', []),
        ('Foo', 'O', '0887-4409', '0887-4409', '', '', []),
        ('Foo', 'O', '0887-4409', '', '', '', []),
        ('Foo', 'O', '', '', '', '', ['xyz']),
        ('Foo', 'O', '0887-4409', '0887-4409', '9780807128237', '', ['EBSCOhost:mzh']),
    ]
    return Title.objects.bulk_create(
        [
            Title(
                name=name,
                pub_type=pub_type,
                issn=issn,
                eissn=eissn,
                isbn=isbn,
                doi=doi,
                proprietary_ids=proprietary_ids,
            )
            for (name, pub_type, issn, eissn, isbn, doi, proprietary_ids) in spec
        ]
    )


@pytest.mark.django_db
class TestLogicTitleManagement:
    def test_find_mergeable_titles_nature(self, natures):
        """
        Real world example of 'Nature' titles
        """
        t1, t2, t3 = natures
        mergeable = list(find_mergeable_titles())
        assert len(mergeable) == 1
        assert len(mergeable[0]) == 2
        assert {t.pk for t in mergeable[0]} == {t1.pk, t2.pk}

    def test_find_mergeable_titles_mla(self, mlas):
        """
        Real world example of many 'MLA' titles where none match
        """
        mergeable = list(find_mergeable_titles())
        assert len(mergeable) == 0

    def test_find_mergeable_titles_many_matching(self, matching_10):
        mergeable = list(find_mergeable_titles())
        assert len(mergeable) == 1
        assert len(mergeable[0]) == 10

    @pytest.mark.clickhouse
    @pytest.mark.usefixtures('clickhouse_on_off')
    @pytest.mark.django_db(transaction=True)
    def test_merge_titles(self, matching_10, settings):
        # the following will create both the access logs and platform-titles
        assert Title.objects.count() == 10
        ImportBatchFullFactory.create_batch(5, create_accesslogs__titles=matching_10)
        assert Title.objects.count() == 10
        for title in matching_10:
            assert title.accesslog_set.count() > 0
            if settings.CLICKHOUSE_SYNC_ACTIVE:
                assert (
                    ch_backend.get_one_record(
                        AccessLogCube.query()
                        .filter(target_id__in=[title.pk])
                        .aggregate(sum=HSum('value'))
                    ).sum
                    > 0
                )
        if settings.CLICKHOUSE_SYNC_ACTIVE:
            title_score = ch_backend.get_records(
                AccessLogCube.query().group_by('target_id').aggregate(sum=HSum('value')),
                auto_use_materialized_views=False,
            )
            assert len(list(title_score)) == 10
        prev_count = AccessLog.objects.count()
        exp_pt_count = (
            PlatformTitle.objects.values('organization', 'platform', 'date').distinct().count()
        )  # only one org, platform for each date
        remaining, _ibs = merge_titles(matching_10)
        assert Title.objects.count() == 1
        assert prev_count == AccessLog.objects.count(), 'accesslog count must be preserved'
        assert prev_count == remaining.accesslog_set.count(), 'all accesslogs belong to remaining'
        assert PlatformTitle.objects.count() == exp_pt_count
        if settings.CLICKHOUSE_SYNC_ACTIVE:
            title_score = ch_backend.get_records(
                AccessLogCube.query().group_by('target_id').aggregate(sum=HSum('value')),
                auto_use_materialized_views=False,
            )
            assert len(list(title_score)) == 1, "only one title in Clickhouse data"


@pytest.mark.django_db
class TestMergeTitles:
    @pytest.mark.parametrize(['do_it'], [(True,), (False,)])
    def test_merge_titles(self, natures, do_it):
        """
        Real world example of 'Nature' titles
        """
        assert Title.objects.count() == 3
        if do_it:
            call_command('merge_titles', '--do-it')
            assert Title.objects.count() == 2, 'two titles get merged'
        else:
            call_command('merge_titles')
            assert Title.objects.count() == 3, 'no change'
