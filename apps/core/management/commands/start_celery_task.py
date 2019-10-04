from django.core.management.base import BaseCommand

from logs.tasks import sync_interest_task, recompute_interest_by_batch_task, \
    import_new_sushi_attempts_task
from sushi.tasks import fetch_new_sushi_data_task, retry_queued_attempts_task


class Command(BaseCommand):

    help = 'Start the specified celery task'

    tasks = {
        'fetch_new_sushi_data_task': fetch_new_sushi_data_task,
        'sync_interest_task': sync_interest_task,
        'recompute_interest_by_batch_task': recompute_interest_by_batch_task,
        'retry_queued_attempts_task': retry_queued_attempts_task,
        'import_new_sushi_attempts_task': import_new_sushi_attempts_task,

    }

    def add_arguments(self, parser):
        parser.add_argument('task')

    def handle(self, *args, **options):
        task_name = options['task']
        task = self.tasks.get(task_name)
        if not task:
            self.stderr.write(self.style.ERROR(f'Cannot find task: {task_name}'))
            self.stderr.write(self.style.WARNING(
                'Available tasks: {}'.format(', '.join(self.tasks.keys()))))
        else:
            self.stderr.write(self.style.SUCCESS(f'Starting task: {task_name}'))
            handle = task.delay()
            self.stderr.write(self.style.SUCCESS(f'Task handle: {handle}'))


