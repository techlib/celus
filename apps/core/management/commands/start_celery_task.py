from django.core.management.base import BaseCommand

from core.tasks import fail_intentionally_task
from logs.tasks import (
    sync_interest_task,
    recompute_interest_by_batch_task,
    import_new_sushi_attempts_task,
    smart_interest_sync_task,
    sync_materialized_reports_task,
)
from recache.tasks import remove_old_cached_queries_task
from sushi.tasks import (
    fetch_new_sushi_data_task,
    retry_queued_attempts_task,
    fetch_new_sushi_data_for_credentials_task,
)
from publications.tasks import erms_sync_platforms_task


class Command(BaseCommand):

    help = 'Start the specified celery task'

    tasks = {
        'fetch_new_sushi_data_task': fetch_new_sushi_data_task,
        'fetch_new_sushi_data_for_credentials_task': fetch_new_sushi_data_for_credentials_task,
        'sync_interest_task': sync_interest_task,
        'recompute_interest_by_batch_task': recompute_interest_by_batch_task,
        'retry_queued_attempts_task': retry_queued_attempts_task,
        'import_new_sushi_attempts_task': import_new_sushi_attempts_task,
        'erms_sync_platforms_task': erms_sync_platforms_task,
        'smart_interest_sync_task': smart_interest_sync_task,
        'fail_intentionally_task': fail_intentionally_task,
        'sync_materialized_reports_task': sync_materialized_reports_task,
        'remove_old_cached_queries_task': remove_old_cached_queries_task,
    }

    def add_arguments(self, parser):
        parser.add_argument('task')
        parser.add_argument('params', nargs='*')

    def handle(self, *args, **options):
        task_name = options['task']
        args = options['params'] or ()
        task = self.tasks.get(task_name)
        if not task:
            self.stderr.write(self.style.ERROR(f'Cannot find task: {task_name}'))
            self.stderr.write(self.style.WARNING('Available tasks:'))
            for key in self.tasks.keys():
                self.stderr.write(self.style.WARNING(f' - {key}'))
        else:
            self.stderr.write(self.style.SUCCESS(f'Starting task: {task_name}'))
            handle = task.delay(*args)
            self.stderr.write(self.style.SUCCESS(f'Task handle: {handle}'))
