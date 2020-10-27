import pytest


@pytest.fixture(scope='function')
def disable_automatic_scheduling(settings):
    settings.AUTOMATIC_HARVESTING_ENABLED = False


@pytest.fixture(scope='function')
def enable_automatic_scheduling(settings):
    settings.AUTOMATIC_HARVESTING_ENABLED = True
