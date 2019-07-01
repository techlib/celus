import pytest

from ..models import Platform


@pytest.fixture
def platforms():
    p1 = Platform.objects.create(ext_id=1, short_name='Plat1', name='Platform 1')
    p2 = Platform.objects.create(ext_id=2, short_name='Plat2', name='Platform 2',
                                 provider='Provider X', url='https://platfrom.provider.test/')
    yield [p1, p2]
