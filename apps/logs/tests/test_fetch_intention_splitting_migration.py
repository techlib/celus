import faker
import pytest
from django.db.models import Count, Sum, F

from logs.logic.split_fetch_intentions import split_fetch_intentions
from test_fixtures.entities.fetchattempts import FetchAttemptFactory

from test_fixtures.entities.scheduler import FetchIntentionQueueFactory


@pytest.mark.django_db
class TestFetchIntentionSplittingMigration:
    @pytest.mark.skip('does not work for some reason - the migration code does not see the data')
    def test_migration(self, migrator):
        # get the models
        other_migrations = [
            ('scheduler', '0011_fetchintention_previous'),
            ('sushi', '0046_fetchintentions_for_fetch_attempts'),
            ('organizations', '0020_organization_unique_shortname'),
            ('publications', '0026_title_type_data_migration'),
        ]
        old_state = migrator.apply_initial_migration(
            [('logs', '0045_dimension_int_to_str'), *other_migrations]
        )
        ReportType = old_state.apps.get_model('logs', 'ReportType')
        Metric = old_state.apps.get_model('logs', 'Metric')
        Platform = old_state.apps.get_model('publications', 'Platform')
        ImportBatch = old_state.apps.get_model('logs', 'ImportBatch')
        AccessLog = old_state.apps.get_model('logs', 'AccessLog')
        Organization = old_state.apps.get_model('organizations', 'Organization')
        SushiFetchAttempt = old_state.apps.get_model('sushi', 'SushiFetchAttempt')
        SushiCredentials = old_state.apps.get_model('sushi', 'SushiCredentials')
        CounterReportType = old_state.apps.get_model('sushi', 'CounterReportType')
        FetchIntention = old_state.apps.get_model('scheduler', 'FetchIntention')
        Harvest = old_state.apps.get_model('scheduler', 'Harvest')

        # prepare some shared instances
        report_type = ReportType.objects.create(short_name="foo_rt")
        metric_a = Metric.objects.create(short_name='A')
        metric_b = Metric.objects.create(short_name='B')
        platform = Platform.objects.create(short_name="foo_pl", ext_id=100)
        organization = Organization.objects.create(
            short_name='foo_org',
            ext_id=1,
            parent=None,
            # mptt related fields which are not auto-populated for some reason
            lft=0,
            rght=1000,
            tree_id=1,
            level=0,
        )
        credentials = SushiCredentials.objects.create(
            organization=organization, platform=platform, counter_version=5
        )
        counter_rt = CounterReportType.objects.create(
            code='foo_x1', counter_version=5, report_type=report_type
        )

        # prepare data
        # prepare 2 import batches spanning more than one month + 1 import batch for one month
        # one of the import batches will be connected to FetchAttempt and FetchIntention
        # the other not
        fake = faker.Faker()
        basic_attrs = {
            'platform': platform,
            'report_type': report_type,
            'organization': organization,
        }
        ib1 = ImportBatch.objects.create(**basic_attrs)
        for date in ['2020-01-01', '2020-02-01', '2020-03-01']:
            for metric in [metric_b, metric_a]:
                AccessLog.objects.create(
                    **basic_attrs, metric=metric, date=date, value=fake.pyint(), import_batch=ib1
                )
        ib2 = ImportBatch.objects.create(**basic_attrs)
        for date in ['2020-03-01', '2020-04-01', '2020-05-01']:
            for metric in [metric_b, metric_a]:
                AccessLog.objects.create(
                    **basic_attrs, metric=metric, date=date, value=fake.pyint(), import_batch=ib2
                )
        ib3 = ImportBatch.objects.create(**basic_attrs)
        for metric in [metric_b, metric_a]:
            date = '2020-01-01'
            AccessLog.objects.create(
                **basic_attrs, metric=metric, date=date, value=fake.pyint(), import_batch=ib3,
            )
        h1 = Harvest.objects.create()
        fa1 = SushiFetchAttempt.objects.create(
            import_batch=ib1,
            start_date='2020-01-01',
            end_date='2020-03-31',
            counter_report=counter_rt,
            credentials=credentials,
        )
        fi1 = FetchIntention.objects.create(
            attempt=fa1,
            start_date=fa1.start_date,
            end_date=fa1.end_date,
            counter_report=fa1.counter_report,
            credentials=fa1.credentials,
            harvest=h1,
        )
        fa3 = SushiFetchAttempt.objects.create(
            import_batch=ib3,
            start_date='2020-01-01',
            end_date='2020-01-31',
            counter_report=counter_rt,
            credentials=credentials,
        )
        fi3 = FetchIntention.objects.create(
            attempt=fa3,
            start_date=fa3.start_date,
            end_date=fa3.end_date,
            counter_report=fa3.counter_report,
            credentials=fa3.credentials,
            harvest=h1,
        )
        # FetchAttempt without ImportBatch
        h2 = Harvest.objects.create()
        fa4 = SushiFetchAttempt.objects.create(
            start_date='2020-01-01',
            end_date='2020-01-31',
            counter_report=counter_rt,
            credentials=credentials,
        )
        fi4 = FetchIntention.objects.create(
            attempt=fa4,
            start_date=fa4.start_date,
            end_date=fa4.end_date,
            counter_report=fa4.counter_report,
            credentials=fa4.credentials,
            harvest=h2,
        )
        # FetchIntention without FetchAttempt
        fi5 = FetchIntention.objects.create(
            start_date='2020-01-01',
            end_date='2020-03-31',
            counter_report=counter_rt,
            credentials=credentials,
            harvest=h2,
        )
        assert ImportBatch.objects.count() == 3
        assert SushiFetchAttempt.objects.count() == 3
        assert FetchIntention.objects.count() == 4

        # Migrate and test
        new_state = migrator.apply_tested_migration(('logs', '0046_one_import_batch_per_month'))
        ImportBatch = new_state.apps.get_model('logs', 'ImportBatch')
        SushiFetchAttempt = new_state.apps.get_model('sushi', 'SushiFetchAttempt')
        FetchIntention = new_state.apps.get_model('scheduler', 'FetchIntention')

        # the tests
        assert FetchIntention.objects.count() == 4 + 2 + 2 + 1, 'fi1 and fi5 split to 3, fi4 to 2'
        assert SushiFetchAttempt.objects.count() == 3 + 2 + 1, 'fa1 splits to 3, fa4 to 2'
        assert ImportBatch.objects.count() == 3 + 2, 'ib1 should split to 3'
        assert (
            ImportBatch.objects.annotate(log_count=Count('accesslog')).filter(log_count=0).count()
            == 0
        ), 'no import batches without accesslogs'

    def test_split_fetch_intentions(self):
        """
        Testing the splitting code outside of a migration. It is much faster than involving
        the migration mechanism and as it turns out, using the `migrator` from
        `django-test-migrations` somehow messes up with the migrations here and the migration
        code sees the database as empty and thus cannot perform the migration correctly

        This code should probably be removed if it starts failing because it is not needed
        for testing all the time - just for migration logs.0046
        """
        from logs.models import ReportType, Metric, AccessLog, ImportBatch
        from sushi.models import SushiCredentials, SushiFetchAttempt, CounterReportType
        from organizations.models import Organization
        from publications.models import Platform
        from scheduler.models import Harvest, FetchIntention

        # prepare some shared instances
        report_type = ReportType.objects.create(short_name="foo_rt")
        metric_a = Metric.objects.create(short_name='A')
        metric_b = Metric.objects.create(short_name='B')
        platform = Platform.objects.create(short_name="foo_pl", ext_id=100)
        organization = Organization.objects.create(
            short_name='foo_org',
            ext_id=1,
            parent=None,
            # mptt related fields which are not auto-populated for some reason
            lft=0,
            rght=1000,
            tree_id=1,
            level=0,
        )
        credentials = SushiCredentials.objects.create(
            organization=organization, platform=platform, counter_version=5
        )
        counter_rt = CounterReportType.objects.create(
            code='foo_x1', counter_version=5, report_type=report_type
        )

        # prepare data
        # prepare 2 import batches spanning more than one month + 1 import batch for one month
        # one of the import batches will be connected to FetchAttempt and FetchIntention
        # the other not
        basic_attrs = {
            'platform': platform,
            'report_type': report_type,
            'organization': organization,
        }
        ib1 = ImportBatch.objects.create(**basic_attrs)
        for i, date in enumerate(['2020-01-01', '2020-02-01', '2020-03-01']):
            for j, metric in enumerate([metric_b, metric_a]):
                AccessLog.objects.create(
                    **basic_attrs,
                    metric=metric,
                    date=date,
                    value=(i + 1) * (j + 1),
                    import_batch=ib1,
                )
        assert ib1.accesslog_set.aggregate(total=Sum('value')) == {'total': 18}
        ib2 = ImportBatch.objects.create(**basic_attrs)
        for i, date in enumerate(['2020-03-01', '2020-04-01', '2020-05-01']):
            for j, metric in enumerate([metric_b, metric_a]):
                AccessLog.objects.create(
                    **basic_attrs,
                    metric=metric,
                    date=date,
                    value=(i + 2) * (j + 1),
                    import_batch=ib2,
                )
        assert ib2.accesslog_set.aggregate(total=Sum('value')) == {'total': 27}
        ib3 = ImportBatch.objects.create(**basic_attrs)
        for i, metric in enumerate([metric_b, metric_a]):
            AccessLog.objects.create(
                **basic_attrs, metric=metric, date='2020-01-01', value=i, import_batch=ib3,
            )
        h1 = Harvest.objects.create()
        fa1 = FetchAttemptFactory.create(
            import_batch=ib1,
            start_date='2020-01-01',
            end_date='2020-03-31',
            counter_report=counter_rt,
            credentials=credentials,
        )
        queue = FetchIntentionQueueFactory(id=1)
        fi1 = FetchIntention.objects.create(
            start_date=fa1.start_date,
            end_date=fa1.end_date,
            counter_report=fa1.counter_report,
            credentials=fa1.credentials,
            harvest=h1,
            when_processed='2021-01-01',
            queue=queue,
        )
        fi1_2 = FetchIntention.objects.create(
            attempt=fa1,
            start_date=fa1.start_date,
            end_date=fa1.end_date,
            counter_report=fa1.counter_report,
            credentials=fa1.credentials,
            harvest=h1,
            queue=queue,
            previous_intention=fi1,
        )
        fa3 = FetchAttemptFactory.create(
            import_batch=ib3,
            start_date='2020-01-01',
            end_date='2020-01-31',
            counter_report=counter_rt,
            credentials=credentials,
        )
        fi3 = FetchIntention.objects.create(
            attempt=fa3,
            start_date=fa3.start_date,
            end_date=fa3.end_date,
            counter_report=fa3.counter_report,
            credentials=fa3.credentials,
            harvest=h1,
        )
        assert h1.intentions.count() == 3
        # FetchAttempt without ImportBatch
        h2 = Harvest.objects.create()
        fa4 = FetchAttemptFactory.create(
            start_date='2020-01-01',
            end_date='2020-02-28',
            counter_report=counter_rt,
            credentials=credentials,
        )
        fi4 = FetchIntention.objects.create(
            attempt=fa4,
            start_date=fa4.start_date,
            end_date=fa4.end_date,
            counter_report=fa4.counter_report,
            credentials=fa4.credentials,
            harvest=h2,
        )
        # FetchIntention without FetchAttempt
        fi5 = FetchIntention.objects.create(
            start_date='2019-12-01',
            end_date='2020-02-28',
            counter_report=counter_rt,
            credentials=credentials,
            harvest=h2,
        )
        assert ImportBatch.objects.count() == 3
        assert SushiFetchAttempt.objects.count() == 3
        assert FetchIntention.objects.count() == 5
        assert (
            FetchIntention.objects.all().values('queue_id').distinct().count() == 4
        ), "one explicit, three auto-generated"

        # Migrate and test

        split_fetch_intentions(AccessLog, FetchIntention)

        # the tests
        assert (
            FetchIntention.objects.count() == 5 + 2 + 2 + 2 + 1
        ), 'fi1+fi1_2 and fi5 split to 3, fi4 to 2'
        assert SushiFetchAttempt.objects.count() == 3 + 2 + 1, 'fa1 splits to 3, fa4 to 2'
        assert ImportBatch.objects.count() == 3 + 2, 'ib1 should split to 3'
        assert (
            ImportBatch.objects.annotate(log_count=Count('accesslog')).filter(log_count=0).count()
            == 0
        ), 'no import batches without accesslogs'
        FetchIntention.objects.exclude(
            start_date__month=F('end_date__month'), start_date__year=F('end_date__year')
        ).count(), "no fetch intention spanning more than one month"
        # do some math
        ib1 = ImportBatch.objects.get(pk=ib1.pk)
        assert ib1.accesslog_set.aggregate(total=Sum('value')) == {'total': 3}, 'split occurred'
        ib2 = ImportBatch.objects.get(pk=ib2.pk)
        assert ib2.accesslog_set.aggregate(total=Sum('value')) == {'total': 27}, 'no split here'
        h1 = Harvest.objects.get(pk=h1.pk)
        assert h1.intentions.count() == 3 + 3 + 1, 'fi1 split into 3, fi1_2 as well'
        # test queue IDs
        # fi1 and fi3 share the same queue ID, so the split intentions should share it as well
        queue_ids = {
            rec['queue_id'] for rec in FetchIntention.objects.all().values('queue_id').distinct()
        }
        assert (
            len(queue_ids) == 9
        ), 'fi1+fi1_2 should split to 3, fi3 stays at 1, fi4 should split to 2, fi5 to 3'
        for queue_id in queue_ids:
            assert (
                FetchIntention.objects.filter(queue_id=queue_id)
                .values('start_date')
                .distinct()
                .count()
                == 1
            ), 'all queues should be for one month only'
        # test previous intentions
        assert (
            h1.intentions.filter(previous_intention__isnull=False).count() == 3
        ), 'fi1_2 should split into 3'
        for fi in h1.intentions.filter(previous_intention__isnull=False):
            assert fi.start_date == fi.previous_intention.start_date
            assert fi.queue_id == fi.previous_intention.queue_id
