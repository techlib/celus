"""
The following tests are not really about the function of the tasks, but rather to make
sure that the tasks do not fail with an error.

The tasks are not run through celery, but as simple functions
"""
import pytest

from .. import tasks


@pytest.mark.django_db
class TestCeleryTasks:
    def test_sync_platforms_with_knowledgebase_task(self):
        tasks.sync_platforms_with_knowledgebase_task()
