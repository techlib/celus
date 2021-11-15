import pytest
from django.core.management import call_command

from logs.models import ImportBatch, AccessLog, Metric
from organizations.tests.conftest import organization_random  # noqa - fixture
from publications.models import Title


@pytest.mark.django_db
class TestRemoveUnusedTitles:
    @pytest.mark.parametrize(['do_it'], [(False,), (True,)])
    def test_command(self, titles, organization_random, platform, interest_rt, do_it):
        ib = ImportBatch.objects.create(
            organization=organization_random, platform=platform, report_type=interest_rt
        )
        metric = Metric.objects.create(short_name='m1', name='Metric 1')
        title1, title2 = titles
        AccessLog.objects.create(
            import_batch=ib,
            organization=organization_random,
            platform=platform,
            report_type=interest_rt,
            date='2020-01-01',
            target=title1,
            metric=metric,
            value=3,
        )
        assert Title.objects.count() == 2
        args = ['--do-it'] if do_it else []
        call_command('remove_unused_titles', *args)
        if do_it:
            assert Title.objects.count() == 1, 'title2 is deleted as it has no usage'
            assert Title.objects.get().pk == title1.pk
        else:
            assert Title.objects.count() == 2, 'no titles is deleted'
