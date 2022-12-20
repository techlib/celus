from pathlib import Path

import pytest
from publications.logic.fake_data import TitleFactory
from tags.logic.scopus_title_list import ScopusTitleListTagger

code_file = Path(__file__).parent / '../../../test-data/tagging_batch/scopus-codes-head.csv'
title_list_file = Path(__file__).parent / '../../../test-data/tagging_batch/scopus-topics-test.csv'


@pytest.mark.django_db
class TestScopusTopicTagging:
    def test_scopus_topic_tagging(self):
        t1 = TitleFactory.create(issn='1234-5678', name='Test title 1')
        t2 = TitleFactory.create(issn='2345-6789', name='Test title 2')
        tagger = ScopusTitleListTagger(title_list_file, code_file)
        tagger.tag_titles()
        assert t1.tags.count() == 3, '1 level 3, 1 level 2, 1 level 1'
        assert t2.tags.count() == 4, '2 level 3, 1 level 2, 1 level 1'
