from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.module_loading import import_string


def fn_name(fullpath):
    return fullpath.split('.')[-1]


class Command(BaseCommand):

    help = 'Start the specified celery task'

    tasks = {fn_name(task_name): task_name for task_name in settings.CELERY_TASK_ROUTES.keys()}

    def add_arguments(self, parser):
        parser.add_argument('task')
        parser.add_argument('params', nargs='*')

    def handle(self, *args, **options):
        task_name = options['task']
        args = options['params'] or ()
        task_path = self.tasks.get(task_name)
        if not task_path:
            self.stderr.write(self.style.ERROR(f'Cannot find task: {task_name}'))
            self.stderr.write(self.style.WARNING('Available tasks:'))
            for key in sorted(self.tasks.keys()):
                self.stderr.write(self.style.WARNING(f' - {key}'))
        else:
            self.stderr.write(self.style.SUCCESS(f'Starting task: {task_name}'))
            task = import_string(task_path)
            handle = task.delay(*args)
            self.stderr.write(self.style.SUCCESS(f'Task handle: {handle}'))
