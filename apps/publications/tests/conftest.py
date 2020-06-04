import pytest

from logs.models import ReportType, Dimension, ReportTypeToDimension
from ..models import Platform, Title


@pytest.fixture
def platforms():
    p1 = Platform.objects.create(ext_id=1, short_name='Plat1', name='Platform 1')
    p2 = Platform.objects.create(
        ext_id=2,
        short_name='Plat2',
        name='Platform 2',
        provider='Provider X',
        url='https://platfrom.provider.test/',
    )
    yield [p1, p2]


@pytest.fixture
def titles():
    t1 = Title.objects.create(name='Title 1', pub_type='B', isbn='123-464-2356', doi='10.1223/x')
    t2 = Title.objects.create(
        name='Title 2', pub_type='J', issn='1234-5678', eissn='2345-6789', doi='10.1234/y'
    )
    yield [t1, t2]


@pytest.fixture
def interest_rt():
    irt = ReportType.objects.create(short_name='interest')
    interest_type_dim = Dimension.objects.create(short_name='Interest_Type')
    ReportTypeToDimension.objects.create(report_type=irt, dimension=interest_type_dim, position=0)
    return irt
