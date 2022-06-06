"""
The following tests are not really about the function of the tasks, but rather to make
sure that the tasks do not fail with an error.

The tasks are not run through celery, but as simple functions
"""
import pytest

from .. import tasks


@pytest.mark.django_db
class TestCeleryTasks:
    def test_clean_obsolete_platform_title_links_task(self):
        tasks.clean_obsolete_platform_title_links_task()

    def test_merge_titles_task(self):
        tasks.merge_titles_task()
