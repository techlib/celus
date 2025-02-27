import pytest
from django.core.management import call_command
from logs.fake_data import ImportBatchFullFactory

from publications.models import Title


@pytest.mark.django_db
class TestRemoveUnusedTitles:
    @pytest.mark.parametrize(["do_it"], [(False,), (True,)])
    def test_command(self, titles, do_it):
        title1 = titles[0]
        ImportBatchFullFactory(create_accesslogs__titles=[title1])
        assert Title.objects.count() == 3
        args = ["--do-it"] if do_it else []
        call_command("remove_unused_titles", *args)
        if do_it:
            assert Title.objects.count() == 1, "title2 and 3 are deleted as they have no usage"
            assert Title.objects.get().pk == title1.pk
        else:
            assert Title.objects.count() == 3, "no titles is deleted"
