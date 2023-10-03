import logging
import pathlib
import typing

from celus_nibbler import NibblerError, Poop, eat
from core.models import DataSource
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from pydantic import ValidationError as PydanticValidationError

logger = logging.getLogger(__name__)


NibblerOutput = typing.List[typing.Union[Poop, NibblerError]]


class ParserDefinitionQuerySet(models.QuerySet):
    def parse_file(self, path: pathlib.Path, platform: str) -> NibblerOutput:
        # Delay nibbler imports to speed up startup
        from celus_nibbler.definitions import Definition
        from celus_nibbler.parsers.dynamic import gen_parser

        definitions = []
        for pd in self:
            try:
                definitions.append(Definition.parse(pd.definition))
            except PydanticValidationError as e:
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
    platforms = ArrayField(
        models.CharField(max_length=100),
        default=list,
        help_text="Platform's short names from knowledgebase",
        blank=True,
    )

    objects = ParserDefinitionQuerySet.as_manager()

    class Meta:
        verbose_name = _('Parser Definition')
        verbose_name_plural = _('Parser Definitions')
        constraints = (
            models.UniqueConstraint(
                fields=['short_name', 'source'], name='parser_def_short_name_source_not_null'
            ),
        )

    def save(self, *args, **kwargs):
        # Delay nibbler imports to speed up startup
        from celus_nibbler.definitions import Definition

        # try to parse
        try:
            nibbler_definition = Definition.parse(self.definition)
        except PydanticValidationError as e:
            raise ValidationError({"definition": str(e)}) from None

        # Extract some fields from JSON
        self.version = nibbler_definition.root.version
        self.short_name = nibbler_definition.root.parser_name
        self.report_type_short_name = nibbler_definition.root.data_format.name
        self.report_type_ext_id = nibbler_definition.root.data_format.id

        # Read platform short_name
        # should accept `"AAA"` and `{"name": "AAA", ...}` formats
        self.platforms = sorted(
            [e["name"] if isinstance(e, dict) else e for e in nibbler_definition.root.platforms]
        )

        return super().save(*args, **kwargs)

    def to_nibbler_definition(self):
        # Delay nibbler imports to speed up startup
        from celus_nibbler.definitions import Definition

        return Definition.parse(self.definition)


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
        source__type=DataSource.TYPE_KNOWLEDGEBASE, ext_id__in=report_types_ext_ids
    )
    if not report_types.exists():
        # Try extract report type using only short_name from global report types
        report_types = ReportType.objects.filter(
            source__type=None, short_name__in=report_types_short_names
        )

    # Note that for now we assume that there is only one knowledgebase
    # DataSource (unique constraint for ReportType short_name)
    return report_types, report_types_short_names
