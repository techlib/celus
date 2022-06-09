import pytest
from django.conf import settings
from django.core.management import call_command, CommandError
from hcube.api.models.aggregation import Count

from logs.cubes import ch_backend, AccessLogCube
from publications.models import Title
from test_fixtures.entities.logs import ImportBatchFullFactory
from test_fixtures.entities.titles import TitleFactory


@pytest.mark.django_db
class TestTitleReimport:
    @pytest.mark.parametrize(['do_it', 'change'], [(True, True), (False, False)])
    def test_prepare_phase(self, do_it, change):
        titles = TitleFactory.create_batch(10)
        for title in titles:
            assert '_foo42_' not in title.name
        if do_it:
            call_command('title_reimport', 'prepare', '--do-it')
        else:
            with pytest.raises(CommandError):
                call_command('title_reimport', 'prepare')
        titles = Title.objects.all()
        for title in titles:
            if change:
                assert title.name.startswith('_foo42_')
            else:
                assert not title.name.startswith('_foo42_')

    @pytest.mark.parametrize(['do_it', 'change'], [(True, True), (False, False)])
    def test_cleanup_phase(self, do_it, change):
        titles = TitleFactory.create_batch(10)
        if do_it:
            call_command('title_reimport', 'cleanup', '--do-it')
        else:
            with pytest.raises(CommandError):
                call_command('title_reimport', 'cleanup')
        assert Title.objects.count() == 0 if do_it else len(titles)

    @pytest.mark.clickhouse
    @pytest.mark.usefixtures('clickhouse_on_off')
    @pytest.mark.django_db(transaction=True)
    def test_resolve_remaining_phase(self):
        title_rem = TitleFactory.create(name='_foo42_Nature', issn='1234-5676', isbn='')
        title_new = TitleFactory.create(name='Nature', issn='1234-5676', isbn='')
        title_rem_no_match = TitleFactory.create(name='_foo42_Future', issn='1234-5687', isbn='')
        ImportBatchFullFactory.create(create_accesslogs__titles=[title_rem])
        ImportBatchFullFactory.create(create_accesslogs__titles=[title_rem_no_match])
        assert title_rem.accesslog_set.count() > 0, 'foo title has usage'
        count_logs = lambda pk: ch_backend.get_one_record(
            AccessLogCube.query().filter(target_id=pk).aggregate(count=Count())
        ).count
        if settings.CLICKHOUSE_SYNC_ACTIVE:
            assert count_logs(title_rem.pk) > 0, 'CH - foo title has usage'
            assert not count_logs(title_new.pk), 'CH - new title has no usage'
        assert title_rem_no_match.accesslog_set.count() > 0, 'foo title has usage'
        assert title_new.accesslog_set.count() == 0, 'new title does not have usage'

        call_command('title_reimport', 'resolve_remaining', '--do-it')

        assert not Title.objects.filter(pk=title_rem.pk).exists(), 'foo title was removed'
        assert title_new.accesslog_set.count() > 0, 'new title has its usage'
        if settings.CLICKHOUSE_SYNC_ACTIVE:
            assert not count_logs(title_rem.pk), 'CH - foo title has no usage'
            assert count_logs(title_new.pk) > 0, 'CH - new title has its usage'
        title_rem_no_match.refresh_from_db()
        assert title_rem_no_match.accesslog_set.count() > 0, 'foo title #2 still has usage'
        assert title_rem_no_match.name == 'Future', '_foo42_ was removed from name'
