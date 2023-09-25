import pytest
from django.core.files.base import ContentFile
from logs.fake_data import ImportBatchFullFactory
from publications.fake_data import TitleFactory
from sushi.fake_data import FetchAttemptFactory

from core.logic.lookup_json_by_title import lookup_json_by_title


@pytest.mark.django_db
class TestLogic:
    def test_lookup_json_by_title(self):
        data_file = ContentFile(b'{"Report_Items": [{"Title": "foo"}]}')
        data_file.name = "something.json"

        t = TitleFactory(name="foo")
        ib = ImportBatchFullFactory(create_accesslogs__titles=[t])
        FetchAttemptFactory(import_batch=ib, data_file=data_file)
        data, errors = lookup_json_by_title(t.id)
        assert data
        assert not errors
