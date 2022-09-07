import logging
import pathlib
import typing

from celus_nibbler import NibblerError, Poop, eat
from celus_nibbler.definitions import Definition
from celus_nibbler.parsers.dynamic import gen_parser
from celus_nigiri import CounterRecord
from core.models import DataSource
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from pydantic import ValidationError as PydantidValidationError

logger = logging.getLogger(__name__)


NibblerOutput = typing.List[typing.Union[Poop, NibblerError]]


class ParserDefinitionQuerySet(models.QuerySet):
    def parse_file(self, path: pathlib.Path, platform: str) -> NibblerOutput:
        definitions = []
        for pd in self:
            try:
                definitions.append(Definition.parse(pd.definition))
            except PydantidValidationError as e:
                logger.warn("Wrong definition (pk=%s): %s", pd.pk, str(e))

        parsers = [gen_parser(e) for e in definitions]

        return eat(path, platform, parsers=r"^nibbler\.dynamic\.", dynamic_parsers=parsers)


class ParserDefinition(models.Model):
    id = models.PositiveIntegerField(primary_key=True)
    source = models.ForeignKey(DataSource, on_delete=models.CASCADE)
    definition = models.JSONField()
    version = models.PositiveIntegerField()
    report_type_short_name = models.CharField(max_length=100)
    report_type_ext_id = models.IntegerField(null=True, blank=True)
    short_name = models.CharField(max_length=100)

    objects = ParserDefinitionQuerySet.as_manager()

    def save(self, *args, **kwargs):
        # try to parse
        try:
            nibbler_definition = Definition.parse(self.definition)
        except PydantidValidationError as e:
            raise ValidationError({"definition": str(e)})

        # Extract some fields from JSON
        self.version = nibbler_definition.__root__.version
        self.short_name = nibbler_definition.__root__.parser_name
        self.report_type_short_name = nibbler_definition.__root__.data_format.name
        self.report_type_ext_id = nibbler_definition.__root__.data_format.id

        return super().save(*args, **kwargs)

    class Meta:
        verbose_name = _('Parser Definition')
        verbose_name_plural = _('Parser Definitions')
        constraints = (
            models.UniqueConstraint(
                fields=['short_name', 'source'], name='parser_def_short_name_source_not_null'
            ),
        )

    def to_nibbler_definition(self) -> Definition:
        return Definition.parse(self.definition)


def is_success(nibbler_output: NibblerOutput) -> bool:
    """ Returns true if nibbler was able to parse at least one sheet """
    return any(isinstance(e, Poop) for e in nibbler_output)


def get_errors(nibbler_output: NibblerOutput) -> typing.List[NibblerError]:
    return [e for e in nibbler_output if isinstance(e, NibblerError)]


def get_report_types_from_nibbler_output(nibbler_output: NibblerOutput) -> models.QuerySet:
    from logs.models import ReportType

    report_types_ext_ids = [
        e.parser.data_format.id
        for e in nibbler_output
        if isinstance(e, Poop) and e.parser.data_format.id
    ]
    report_types_short_names = [
        e.parser.data_format.name for e in nibbler_output if isinstance(e, Poop)
    ]

    # TODO this should be updated when multiple knowledgebases are used (hopefully never)
    report_types = ReportType.objects.filter(
        source__type=DataSource.TYPE_KNOWLEDGEBASE, ext_id__in=report_types_ext_ids,
    )
    if not report_types.exists():
        # Try extract report type using only short_name from global report types
        report_types = ReportType.objects.filter(
            source__type=None, short_name__in=report_types_short_names
        )

    # Note that for now we assume that there is only one knowledgebase
    # DataSource (unique constraint for ReportType short_name)
    return report_types, report_types_short_names


def get_records_from_nibbler_output(
    nibbler_output: NibblerOutput,
) -> typing.Generator[CounterRecord, None, None]:
    for poop in [e for e in nibbler_output if isinstance(e, Poop)]:
        for record in poop.records():
            yield record
