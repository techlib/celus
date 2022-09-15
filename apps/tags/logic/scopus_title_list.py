import csv
import logging
from pathlib import Path
from typing import Union, Optional, Callable, Iterable

from django.db.models import Q

from logs.logic.validation import normalize_issn
from publications.models import Title
from tags.models import AccessibleBy, Tag, TagClass, TagScope, TaggingBatch, TitleTag

logger = logging.getLogger(__name__)


class ScopusTitleListTagger:

    LEVEL_TO_COLOR = {'Level 1': '#ef90a3', 'Level 2': '#f1b1be', 'Level 3': '#f5cdd5'}
    DEFAULT_COLOR = '#ed6d86'

    def __init__(self, title_list_file: Union[str, Path], class_code_file: Union[str, Path]):
        self.title_list_file = title_list_file
        self.class_code_file = class_code_file
        self._class_code_map = self._load_class_code_map(self.class_code_file)
        self._issn_to_code_map = self._load_issn_to_code_map(self.title_list_file)
        self._level_to_tag_class = {}
        self._name_to_tag = {}

    @classmethod
    def _load_class_code_map(cls, fname: str) -> dict:
        class_code_map = {}
        with open(fname) as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row.pop('Code')
                class_code_map[code] = {k.strip(): v.strip() for k, v in row.items()}
        return class_code_map

    @classmethod
    def _load_issn_to_code_map(cls, fname: str) -> dict:
        issn_to_code_map = {}
        with open(fname) as f:
            reader = csv.DictReader(f)
            for row in reader:
                issn = normalize_issn(row['ISSN'].strip(), raise_error=False)
                eissn = normalize_issn(row['eISSN'].strip(), raise_error=False)
                if codes := [code.strip() for code in row['Codes'].split(';') if code.strip()]:
                    if issn:
                        issn_to_code_map[issn] = codes
                    if eissn:
                        issn_to_code_map[eissn] = codes
        return issn_to_code_map

    def tag_titles(
        self,
        progress_monitor: Optional[Callable[[int, int], None]] = None,
        levels: Optional[Iterable] = None,
        batch_size=10_000,
    ):
        to_insert = []
        batch = TaggingBatch.objects.create(internal_name='scopus-topics')
        titles = Title.objects.filter(~Q(issn='') | ~Q(eissn=''))
        total = titles.count()
        for i, title in enumerate(titles.iterator()):
            for issn in (title.issn, title.eissn):
                if not issn:
                    continue
                for code in self._issn_to_code_map.get(issn, []):
                    for level, topic in self._class_code_map.get(code, {}).items():
                        if levels and level not in levels:
                            continue
                        if level not in self._level_to_tag_class:
                            (
                                self._level_to_tag_class[level],
                                _created,
                            ) = TagClass.objects.get_or_create(
                                internal=True,
                                name=self.level_to_class_name(level),
                                scope=TagScope.TITLE,
                                defaults={
                                    'desc': f'Topics from the Scopus title list - {level}',
                                    'bg_color': self.LEVEL_TO_COLOR.get(level, self.DEFAULT_COLOR),
                                    'can_modify': AccessibleBy.SYSTEM,
                                    'can_create_tags': AccessibleBy.SYSTEM,
                                    'default_tag_can_see': AccessibleBy.EVERYBODY,
                                    'default_tag_can_assign': AccessibleBy.SYSTEM,
                                },
                            )
                        if (level, topic) not in self._name_to_tag:
                            self._name_to_tag[(level, topic)], _created = Tag.objects.get_or_create(
                                name=topic,
                                tag_class=self._level_to_tag_class[level],
                                defaults={
                                    'desc': f'{level} topic from the Scopus title list - {topic}',
                                    'bg_color': self.LEVEL_TO_COLOR.get(level, self.DEFAULT_COLOR),
                                    'can_see': AccessibleBy.EVERYBODY,
                                    'can_assign': AccessibleBy.SYSTEM,
                                },
                            )
                        tag = self._name_to_tag[(level, topic)]
                        to_insert.append(
                            TitleTag(
                                tag_id=tag.pk,
                                target_id=title.pk,
                                tagging_batch=batch,
                                _tag_class=tag.tag_class,
                                _exclusive=tag.tag_class.exclusive,
                                last_updated_by=None,
                            )
                        )
            if len(to_insert) >= batch_size:
                TitleTag.objects.bulk_create(to_insert, ignore_conflicts=True)
                to_insert = []
                if progress_monitor:
                    progress_monitor(i, total)
        if to_insert:
            TitleTag.objects.bulk_create(to_insert, ignore_conflicts=True)
            if progress_monitor:
                progress_monitor(total, total)

    @classmethod
    def level_to_class_name(cls, level: str) -> str:
        return level.replace('Level ', 'Scopus #')
