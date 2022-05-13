import pytest
from django.core.management import call_command, CommandError

from publications.models import Title
from test_fixtures.entities.titles import TitleFactory


@pytest.mark.django_db
class TestTitleReimport:
    @pytest.mark.parametrize(['do_it', 'change'], [(True, True), (False, False)])
    def test_prepare_phase(self, do_it, change):
        titles = TitleFactory.create_batch(10)
        for title in titles:
            assert '_foo42_' not in title.name
        if do_it:
            call_command('title_reimport', 'prepare', '--do-it')
        else:
            with pytest.raises(CommandError):
                call_command('title_reimport', 'prepare')
        titles = Title.objects.all()
        for title in titles:
            if change:
                assert title.name.startswith('_foo42_')
            else:
                assert not title.name.startswith('_foo42_')

    @pytest.mark.parametrize(['do_it', 'change'], [(True, True), (False, False)])
    def test_cleanup_phase(self, do_it, change):
        titles = TitleFactory.create_batch(10)
        if do_it:
            call_command('title_reimport', 'cleanup', '--do-it')
        else:
            with pytest.raises(CommandError):
                call_command('title_reimport', 'cleanup')
        assert Title.objects.count() == 0 if do_it else len(titles)

    # def test_cleanup_phase(self):
    #     titles = TitleFactory.create_batch(10)
    #     id_to_name = {}
    #     for title in titles:
    #         assert '_foo42_' not in title.name
    #         id_to_name[title.pk] = title.name
    #     call_command('title_reimport', 'prepare')
    #     titles = Title.objects.all()
    #     for title in titles:
    #         assert title.name.startswith('_foo42_')
    #     call_command('title_reimport', 'cleanup')
    #     for title in titles:
    #         assert not title.name.startswith('_foo42_')
    #         assert title.name == id_to_name[title.pk]
