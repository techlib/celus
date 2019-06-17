import pytest

from ..models import Organization


@pytest.fixture()
def organizations():
    parent1 = Organization.objects.create(ext_id=1, parent=None, internal_id='AAA', ico='123',
                                          name_cs='AAA', name_en='AAA', short_name='AA')
    parent2 = Organization.objects.create(ext_id=2, parent=None, internal_id='BBB', ico='234',
                                          name_cs='BBB', name_en='BBB', short_name='BB')
    child1 = Organization.objects.create(ext_id=3, parent=parent1, internal_id='AAA1', ico='1231',
                                         name_cs='AAA1', name_en='AAA1', short_name='AA1')
    return [parent1, parent2, child1]
