import codecs
import logging
import tempfile
from abc import ABC, abstractmethod
from itertools import chain, islice
from typing import TYPE_CHECKING, Any, Callable, List, Optional, TextIO, Tuple, Type, Union
from zipfile import ZIP_DEFLATED, ZipFile

from cachalot.api import cachalot_disabled
from core.logic.debug import log_memory
from core.models import User
from django.conf import settings
from django.db.models import Field, ForeignKey, Model, QuerySet
from django.db.models.base import ModelBase
from django.utils.text import slugify
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.utils.translation import pgettext
from export.enums import FileFormat
from mptt.models import MPTTModelBase
from organizations.models import Organization
from tags.models import Tag, TagScope, UserTagClass

from logs.logic.export_utils import (
    CSVListWriter,
    DictWriter,
    Formula,
    ListWriter,
    MappingCSVDictWriter,
    MappingXlsxDictWriter,
    XlsxListWriter,
)
from logs.logic.reporting.slicer import FlexibleDataSlicer, SlicerConfigError, SlicerConfigErrorCode
from logs.models import AccessLog, DimensionText, ReportType

if TYPE_CHECKING:
    from xlsxwriter.workbook import Workbook

logger = logging.getLogger(__name__)


class FlexibleDataExporter(ABC):
    object_remapped_dims = {
        "target": {"columns": ["name", "issn", "eissn", "isbn"]},
        "item": {"columns": ["name", "doi", "issn", "eissn", "isbn", "publication_date"]},
    }

    dim_name_to_column_name = {"publication_date": _("Publication date")}

    taggable_rows = {
        "target": {"scope": TagScope.TITLE, "related_attr": "title"},
        "platform": {"scope": TagScope.PLATFORM, "related_attr": "platform"},
        "organization": {"scope": TagScope.ORGANIZATION, "related_attr": "organization"},
    }
    tag_delimiter = " | "

    def __init__(
        self,
        slicer: FlexibleDataSlicer,
        column_parts_separator: str = " / ",
        report_name: str = "",
        report_owner: Optional[User] = None,
        report_owner_org: Optional[Organization] = None,
        include_tags: bool = False,  # tag column will be added to the report
        include_row_totals: bool = False,  # row totals will be added to the report
        include_col_totals: bool = False,  # column totals will be added to the report
    ):
        self.slicer = slicer
        self.report_name = report_name
        self.report_owner = report_owner
        self.report_owner_org = report_owner_org
        if self.report_owner_org and self.report_owner:
            raise ValueError("Only one of `report_owner` and `report_owner_org` should be set")
        self._include_tags = include_tags
        self.include_row_totals = include_row_totals
        if self.include_row_totals and self.slicer.trend_mode:
            logger.warning("Row totals are not supported in trend mode")
            self.include_row_totals = False
        self.include_col_totals = include_col_totals
        if self.include_tags and not (self.report_owner or self.report_owner_org):
            raise ValueError(
                "`report_owner` or `report_owner_org` must be set if `include_tags` is True "
                "because tags are user/org-specific"
            )

        self.involved_report_types = self.slicer.involved_report_types()
        self.column_parts_separator = column_parts_separator

        # Handle multiindex support - store metadata for all primary dimensions
        self.primary_dim_keys = []
        self.primary_dim_metadata = []  # list of (explicit, remapped, model) tuples
        self.prim_dim_remap = {}  # dict mapping pk keys to their remappings

        for i, primary_dimension in enumerate(self.slicer.primary_dimensions):
            # Resolve dimension metadata first so we know how the slicer outputs the key
            explicit, remapped, model = self.resolve_dimension(primary_dimension)

            # All primary dimensions now use pk, pk2, pk3, etc. keys consistently
            # regardless of whether it's single-dimension or multiindex
            key = self.slicer.get_pk_key(i)

            self.primary_dim_keys.append(key)
            self.primary_dim_metadata.append((explicit, remapped, model, primary_dimension))

            # Initialize remap storage for this dimension
            self.prim_dim_remap[key] = {}

        self._fields = []
        # mapping between primary dim value and connected tags, used in batch processing
        # inside write_qs_to_output
        self._tag_cache = {}

    @property
    def include_tags(self):
        # For multiindex, tags should be included if ANY primary dimension is taggable
        return (
            self._include_tags
            and any(dim in self.taggable_rows for dim in self.slicer.primary_dimensions)
            and not self.slicer.tag_roll_up
        )

    @include_tags.setter
    def include_tags(self, value):
        self._include_tags = value

    @property
    def effective_prim_dim(self) -> str:
        if not self.slicer.tag_roll_up:
            return self.slicer.primary_dimensions[0]
        return "tag"

    @property
    def multiindex(self) -> bool:
        return len(self.slicer.primary_dimensions) > 1

    def remapped_keys(self):
        return self.object_remapped_dims.get(self.effective_prim_dim, {}).get("columns", ["name"])

    def prepare_primary_remap(self, batch_dict: dict):
        """
        :param batch_dict: dict mapping pk keys ("pk", "pk2", etc.) to sets of values to remap
        """
        for key, batch in batch_dict.items():
            if not batch:
                continue

            # Find the metadata for this primary dimension
            idx = self.primary_dim_keys.index(key)
            explicit, remapped, model, dim_name = self.primary_dim_metadata[idx]

            if remapped:
                if explicit:
                    log_memory(f"FlexibleDataExporter - before creating remap for explicit {key}")
                    self.prim_dim_remap[key] = dict(
                        rec
                        for rec in DimensionText.objects.filter(
                            dimension=model, pk__in=batch
                        ).values_list("pk", "text")
                    )
                    log_memory(f"FlexibleDataExporter - after creating remap for explicit {key}")
                else:
                    log_memory(f"FlexibleDataExporter - before creating remap for implicit {key}")
                    # For tag_roll_up, use "tag" as the effective dimension name
                    effective_dim = (
                        "tag"
                        if (key == "pk" and self.slicer.tag_roll_up and model.__name__ == "Tag")
                        else dim_name
                    )
                    self.prim_dim_remap[key] = self._prepare_implicit_remap(
                        model.objects.filter(pk__in=batch), effective_dim
                    )
                    log_memory(f"FlexibleDataExporter - after creating remap for implicit {key}")

    def _prepare_implicit_remap(self, qs: QuerySet, dim_name: str = None) -> dict:
        # Fallback to name->short_name (e.g. for Metric)
        with cachalot_disabled():
            # Get remapped keys for the specific dimension, not just the first one
            if dim_name:
                remapped_keys = self.object_remapped_dims.get(dim_name, {}).get("columns", ["name"])
            else:
                remapped_keys = self.remapped_keys()

            if "name" in remapped_keys and hasattr(qs.model, "short_name"):
                remaps = list(qs.values("pk", "short_name", *remapped_keys))
                for item in remaps:
                    if not item["name"].strip():
                        item["name"] = item["short_name"] or ""
                    del item["short_name"]
                return {obj["pk"]: tuple(obj[k] for k in remapped_keys) for obj in remaps}

            return {
                obj["pk"]: tuple(obj[k] for k in remapped_keys)
                for obj in qs.values("pk", *remapped_keys)
            }

    @abstractmethod
    def stream_data_to_sink(
        self, sink, progress_monitor: Optional[Callable[[int, int], None]] = None
    ) -> int:
        """
        If progress monitor is given, it will be called with a tuple (current_count, total_count)
        for each bunch of exported rows. It will also be called at the end of export.

        Please note that in order to calculate the total the query has to be run twice
        which might incur some time penalty.

        Returns the number of written rows.
        """

    @abstractmethod
    def create_writer(self, output, fields: list) -> DictWriter:
        """
        Creates a DictWriter instance suitable for this exporter.
        """

    def write_qs_to_output(
        self,
        output: TextIO,
        qs: QuerySet,
        extra_row_fn: Optional[Callable[[], dict]] = None,
        progress_monitor: Optional[Callable[[int, int], None]] = None,
        batch_size=1000,
        **kwargs,
    ) -> int:
        """
        :param output: output stream - a file-like object
        :param qs: QuerySet to export
        :param batch_size: when fetching tags, how many rows at once to process
        :param extra_row_fn: a function that returns a dict with one extra row to be added to the
                             output
        :param progress_monitor: a function that will be called with a tuple
                                (current_count, total_count) during the export
        `kwargs` will be passed to the writer
        """
        total = 0
        if progress_monitor:
            # we put out the total as soon as possible
            total = qs.count()
            if extra_row_fn:
                total += 1
            progress_monitor(0, total)
        data = qs.iterator()
        try:
            row = next(data)
        except StopIteration:
            return 0

        # Create fields for all primary dimensions
        fields = []
        for key, (explicit, remapped, _model, dim_name) in zip(
            self.primary_dim_keys, self.primary_dim_metadata, strict=True
        ):
            # Add the main column for this primary dimension
            fields.append((key, self.dimension_output_name(dim_name)))

            # Add extra columns for dimensions with remapped attributes
            # Skip this when tag_roll_up is True since the actual dimension is "tag", not the
            # configured primary dimension
            if remapped and not explicit and not self.slicer.tag_roll_up:
                # Get the remapped keys for this specific dimension
                dim_remap_keys = self.object_remapped_dims.get(dim_name, {}).get(
                    "columns", ["name"]
                )
                for remap_key in dim_remap_keys[1:]:  # Skip first (main) column
                    # For backward compatibility, only prefix with key when multiindex
                    if self.multiindex:
                        field_key = f"{key}_{remap_key}"
                    else:
                        field_key = remap_key
                    column_name = self.dim_name_to_column_name.get(remap_key, remap_key.upper())
                    fields.append((field_key, column_name))

            # Add tags column right after this dimension if it's taggable
            if (
                self._include_tags
                and dim_name in self.taggable_rows
                and not self.slicer.tag_roll_up
            ):
                # For multiindex, use prefixed key; for single dimension, use "tags"
                if self.multiindex:
                    tag_key = f"{key}_tags"
                    # Include dimension name in column header for clarity
                    tag_column_name = f"{self.dimension_output_name(dim_name)} {_('Tags')}"
                else:
                    tag_key = "tags"
                    tag_column_name = _("Tags")
                fields.append((tag_key, tag_column_name))
        # add total column if needed
        if self.include_row_totals:
            fields.append(("_total", _("Row total")))
        # trend mode has implicit columns
        if self.slicer.trend_mode:
            fields.append((self.slicer.COL_BASE, self.slicer.base_subset_filters[0].smart_str()))
            fields.append(
                (self.slicer.COL_COMPARED, self.slicer.compared_subset_filters[0].smart_str())
            )
            fields.append((self.slicer.COL_DIFF, pgettext("column name", "Change")))
            fields.append((self.slicer.COL_REL_DIFF, _("Change %")))
        # fields from groups
        other_fields = []
        for key in row:
            if key.startswith("grp-"):
                other_fields.append((key, self.remap_column_name(key)))
        # sort columns by their remapped name
        other_fields.sort(key=lambda x: (x[1], x[0]))
        fields += other_fields
        self._fields = fields
        writer = self.create_writer(output, fields)
        count = 0

        # we need to get the first row back into the data
        all_data = chain(
            [row], data, [{"no_remap": True, **extra_row_fn()}] if extra_row_fn else []
        )
        while batch := list(islice(all_data, batch_size)):
            # Extract pks for all primary dimensions
            batch_pks = {}
            for key in self.primary_dim_keys:
                batch_pks[key] = {
                    obj[key] for obj in batch if not obj.get("no_remap") and key in obj
                }

            # potentially prefetch tags for all taggable dimensions
            if self.include_tags:
                self._tag_cache = {}  # Maps (dim_key, pk_value) to list of tags
                for key, (_explicit, _remapped, _model, dim_name) in zip(
                    self.primary_dim_keys, self.primary_dim_metadata, strict=True
                ):
                    if dim_name not in self.taggable_rows:
                        continue

                    tag_spec = self.taggable_rows[dim_name]
                    link_class = Tag.link_class_from_scope(tag_spec["scope"])
                    dim_pks = batch_pks[key]

                    if not dim_pks:
                        continue

                    if self.report_owner:
                        # get the tags visible for the report_owner
                        # the user does not want to see following tag classes in output
                        hidden_tag_classes = UserTagClass.objects.filter(
                            user=self.report_owner, hidden=True
                        ).values_list("tag_class_id", flat=True)
                        link_qs = link_class.objects.filter(
                            tag__in=Tag.objects.user_accessible_tags(self.report_owner),
                            target_id__in=dim_pks,
                        ).exclude(tag__tag_class__in=hidden_tag_classes)
                    else:
                        # if report_onwer is not set, we must have report_owner_org set
                        # checked in __init__. But I add the check here as well.
                        if not self.report_owner_org:
                            raise ValueError("report_owner or report_owner_org must be set.")
                        # get the tags visible for the report_owner_org
                        link_qs = link_class.objects.filter(
                            tag__in=Tag.objects.org_accessible_tags(self.report_owner_org),
                            target_id__in=dim_pks,
                        )

                    for link in link_qs.select_related("tag", "tag__tag_class"):
                        cache_key = (key, link.target_id)
                        self._tag_cache.setdefault(cache_key, []).append(link.tag)

            self.prepare_primary_remap(batch_pks)
            for row in batch:
                self.writerow(writer, row)
                count += 1
                if progress_monitor and count % 100 == 0:
                    progress_monitor(count, total)
        if progress_monitor:
            progress_monitor(total, total)
        writer.finalize()
        return count

    def writerow(self, writer, row):
        # Remap all primary dimensions and add their tags
        for key, (explicit, remapped, _model, dim_name) in zip(
            self.primary_dim_keys, self.primary_dim_metadata, strict=True
        ):
            if key not in row:
                continue

            # Save the original ID before remapping (needed for tag lookup)
            original_pk = row[key]

            if remapped:
                if explicit:
                    # remap to text using the DimensionText mapping
                    row[key] = self.prim_dim_remap[key].get(row[key], row[key])
                else:
                    # mapper converts to dict with multiple attributes
                    if remap_data := self.prim_dim_remap[key].get(row[key]):
                        # Get the remapped keys for this specific dimension
                        dim_remap_keys = self.object_remapped_dims.get(dim_name, {}).get(
                            "columns", ["name"]
                        )
                        _prim_key, *extra_keys = dim_remap_keys
                        prim_text, *extra_data = remap_data
                        row[key] = prim_text
                        if self.slicer.tag_roll_up:
                            # when tag_roll_up is enabled, the primary dimension is the tagged
                            # dimension. But we cannot assign its extra attributes to the tag
                            # (for example, ISSN, EISSN, ISBN for title)
                            # so we skip the whole extra attributes assignment
                            # This section is here so that we have explicit comment about this
                            # situation and to provide a place for possible future implementation
                            # of tag-related extra attributes.
                            pass
                        else:
                            # remap all other keys for this dimension
                            for extra_key, text in zip(extra_keys, extra_data, strict=True):
                                # For backward compatibility, only prefix with key when multiindex
                                if self.multiindex:
                                    row[f"{key}_{extra_key}"] = text
                                else:
                                    row[extra_key] = text
            else:
                # For non-remapped fields (like date fields), preserve the value as-is
                # The value is already in the correct format from the database query
                pass

            # Add tags column for this dimension if it's taggable
            if self.include_tags and dim_name in self.taggable_rows:
                # For multiindex, use prefixed key; single dim uses "tags"
                if self.multiindex:
                    tag_key = f"{key}_tags"
                else:
                    tag_key = "tags"
                # Use original PK (before remapping) for tag lookup
                cache_key = (key, original_pk)
                row[tag_key] = self.tag_delimiter.join(
                    sorted(t.full_name for t in self._tag_cache.get(cache_key, []))
                )

        writer.writerow(row)

    def translate_part_key(self, part_key: [Tuple[str, Any]]):
        out = []
        for key in self.slicer.split_by:
            out.append(self.dimension_remap(key, part_key[key]))
        return out

    def remap_column_name(self, column):
        parts = self.slicer.decode_key(column)
        name_parts = []
        for key, value in parts.items():
            name_parts.append(self.dimension_remap(key, value))
        return self.column_parts_separator.join(name_parts)

    def dimension_output_name(self, dim_name: str) -> str:
        explicit, _remapped, dim_model = self.resolve_dimension(dim_name)
        if explicit:
            return dim_model.name or dim_model.short_name
        if isinstance(dim_model, (ModelBase, MPTTModelBase)):
            return str(dim_model._meta.verbose_name)
        # dim_model must be a Field, but let's make sure
        if isinstance(dim_model, Field):
            return str(dim_model.verbose_name)
        raise ValueError(f"Could not resolve dimension: {dim_name}")

    def dimension_remap(self, dimension, value):
        if value is None:
            return "-"
        explicit, remapped, dim_model = self.resolve_dimension(dimension)
        if remapped:
            if explicit:
                obj = DimensionText.objects.get(pk=value)
                return obj.text_local or obj.text
            else:
                obj = dim_model.objects.get(pk=value)
                return obj.name or obj.short_name
        else:
            return str(value)

    def resolve_dimension(self, ref) -> Tuple[bool, bool, Union[Type[Model], Model, Field]]:
        """
        :param ref: attribute name referencing this dimension in AccessLog
        :return: (explicit, remapped, Dimension instance or references model)
        """
        field, _modifier = AccessLog.get_dimension_field(ref)
        if isinstance(field, ForeignKey):
            if ref == self.slicer.primary_dimensions[0] and self.slicer.tag_roll_up:
                return False, True, Tag
            return False, True, field.remote_field.model
        elif ref.startswith("dim"):
            # we need the report types to deal with this
            # the slicer should ensure that all `dim`s between different report types are the same
            rt: ReportType = self.involved_report_types[0]
            dim = rt.dimension_by_attr_name(ref)
            return True, True, dim
        else:
            return False, False, field

    def create_report_metadata(self, writer: ListWriter):
        writer.writerow([_("Report name"), self.report_name])
        writer.writerow([_("Created"), str(now())])
        writer.writerow([_("Created for"), str(self.report_owner or self.report_owner_org)])
        writer.writerow([_("CELUS version"), str(settings.CELUS_VERSION)])
        writer.writerow(["", ""])

        # coverage for normal vs trend mode
        coverage = self.slicer.get_coverage()
        if coverage:
            if self.slicer.trend_mode:
                coverage_base = coverage["base"]["ratio"] * 100
                coverage_compared = coverage["compared"]["ratio"] * 100
                writer.writerow(
                    [
                        _("Data coverage"),
                        _("Base period: %(coverage).1f%%") % {"coverage": coverage_base},
                        _("Compared period: %(coverage).1f%%") % {"coverage": coverage_compared},
                    ]
                )
            else:
                if coverage["overall"]["ratio"] is not None:
                    coverage_overall = coverage["overall"]["ratio"] * 100
                    writer.writerow([_("Data coverage"), f"{coverage_overall:.1f}%"])
                else:
                    writer.writerow([_("Data coverage"), "-"])

        writer.writerow(
            [
                _("Split by"),
                ", ".join(self.dimension_output_name(dim) for dim in self.slicer.split_by)
                if self.slicer.split_by
                else "-",
            ]
        )
        # Show all primary dimensions
        writer.writerow(
            [
                _("Rows"),
                ", ".join(
                    self.dimension_output_name(dim) for dim in self.slicer.primary_dimensions
                ),
            ]
        )
        # columns depend on the trend_mode
        if self.slicer.trend_mode:
            start = self.slicer.base_subset_filters[0].smart_str()
            end = self.slicer.compared_subset_filters[0].smart_str()
            columns = _("Trend analysis: %(start)s vs %(end)s") % {"start": start, "end": end}
        else:
            columns = "; ".join(self.dimension_output_name(dim) for dim in self.slicer.group_by)
        writer.writerow([_("Columns"), columns])
        for i, fltr in enumerate(self.slicer.dimension_filters):
            writer.writerow(
                [_("Applied filters") if i == 0 else "", self.slicer.filter_to_str(fltr)]
            )
        # print out organizations for which the report was created in case they would be "hidden"
        # (not present in rows, cols, split_by or filter)
        dim = "organization"
        if (
            not self.report_owner_org  # if we have org, we know it's included
            and dim not in self.slicer.primary_dimensions  # Check all primary dimensions
            and dim not in self.slicer.split_by
            and dim not in self.slicer.group_by
            and not any(f.dimension == dim for f in self.slicer.dimension_filters)
        ):
            writer.writerow([])
            writer.writerow(
                [
                    _("Included organizations"),
                    _(
                        "(No organization filter was applied, the data represent the following "
                        "organizations)"
                    ),
                ]
            )
            if self.slicer.organization_filter:
                # if an explicit filter was applied, use it
                orgs = self.slicer.organization_filter
            elif self.report_owner:
                # otherwise, use what user has access to
                orgs = self.report_owner.accessible_organizations()
            else:
                # if nothing is available, ask the slicer itself
                orgs = Organization.objects.filter(
                    pk__in=[
                        rec["organization"]
                        for rec in self.slicer.get_possible_dimension_values_queryset(
                            "organization"
                        )
                    ]
                )
            for org in orgs.order_by("name"):
                writer.writerow(["", org.name])

    def _remainder_fn(self, part=None):
        if self.slicer.show_untagged_remainder:
            return lambda: {
                "pk": _("-- untagged remainder --"),
                **self.slicer.get_remainder(part=part),
            }
        return None

    def create_formulas(self, fields):
        formulas = []
        if self.slicer.trend_mode:
            # in trend mode, we have column with difference and relative difference.
            # the relative difference should be formatted as percent and also needs the total to be
            # calculated differently then just summing up the individual values
            formulas.append(
                Formula(
                    key=self.slicer.COL_DIFF,
                    operation="{1}-{0}",
                    refs=[self.slicer.COL_BASE, self.slicer.COL_COMPARED],
                )
            )
            formulas.append(
                Formula(
                    key=self.slicer.COL_REL_DIFF,
                    operation="({1}-{0})/{0}",
                    fn=lambda a, b: ((b - a) / a) if a else None,
                    refs=[self.slicer.COL_BASE, self.slicer.COL_COMPARED],
                )
            )

        elif self.include_row_totals:
            # include row totals is incompatible with trend mode
            formulas.append(
                Formula(
                    key="_total",
                    operation="sum",
                    refs=[key for key, _field in fields if key.startswith("grp-")],
                )
            )
        return formulas

    def sum_row_skip_cols(self) -> int:
        # Count all primary dimension columns (including extra attributes like ISSN, ISBN, and tags)
        skip = 0
        for explicit, remapped, _model, dim_name in self.primary_dim_metadata:
            skip += 1  # Main column for this dimension
            if remapped and not explicit:
                # Add extra columns (e.g., ISSN, EISSN, ISBN for title)
                remap_keys = self.object_remapped_dims.get(dim_name, {}).get("columns", ["name"])
                skip += len(remap_keys) - 1  # -1 because first is main column

            # Add tags column for this dimension if it's taggable
            if self.include_tags and dim_name in self.taggable_rows:
                skip += 1

        return skip

    def _check_maximum_parts_number(self, total: int):
        if total > self.slicer.MAXIMUM_POSSIBLE_PARTS:
            raise SlicerConfigError(
                f"Too many parts to export ({total}). Please refine you report to lower "
                f"the number of parts.",
                code=SlicerConfigErrorCode.E112,
            )


class FlexibleDataSimpleCSVExporter(FlexibleDataExporter):
    """
    Simple CSV output exporter which does not support multipart output and/or metadata output
    """

    def stream_data_to_sink(
        self, sink, progress_monitor: Optional[Callable[[int, int], None]] = None
    ):
        qs = self.slicer.get_data()
        self.write_qs_to_output(
            sink, qs, extra_row_fn=self._remainder_fn(), progress_monitor=progress_monitor
        )

    def create_writer(self, output, fields: list) -> DictWriter:
        return MappingCSVDictWriter(
            output,
            fields=fields,
            row_formulas=self.create_formulas(fields),
            include_col_totals=self.include_col_totals,
            sum_row_skip_cols=self.sum_row_skip_cols(),
        )


class FlexibleDataZipCSVExporter(FlexibleDataSimpleCSVExporter):
    """
    Exporter creating zipped CSV files with support for metadata and multipart output
    """

    def stream_data_to_sink(
        self, sink, progress_monitor: Optional[Callable[[int, int], None]] = None
    ):
        parts = self.slicer.get_parts_queryset() if self.slicer.split_by else None
        with ZipFile(sink, "w", compression=ZIP_DEFLATED) as outzip:
            # add metadata sheet
            with outzip.open("_metadata.csv", "w", force_zip64=True) as outfile:
                encoder = codecs.getwriter("utf-8")(outfile)
                writer = CSVListWriter(encoder)
                self.create_report_metadata(writer)
                writer.finalize()

            # output data itself
            if parts is None:
                qs = self.slicer.get_data()
                extra_row_fn = self._remainder_fn()
                fname = "report"
                with outzip.open(fname + ".csv", "w", force_zip64=True) as outfile:
                    writer = codecs.getwriter("utf-8")
                    encoder = writer(outfile)
                    self.write_qs_to_output(
                        encoder, qs, extra_row_fn=extra_row_fn, progress_monitor=progress_monitor
                    )
            else:
                total = parts.count()
                self._check_maximum_parts_number(total)
                for i, part in enumerate(parts):
                    key = [part[name] for name in self.slicer.split_by]
                    qs = self.slicer.get_data(part=key)
                    extra_row_fn = self._remainder_fn(part=key)
                    fname = "-".join([slugify(p) for p in self.translate_part_key(part)])
                    with outzip.open(fname + ".csv", "w", force_zip64=True) as outfile:
                        writer = codecs.getwriter("utf-8")
                        encoder = writer(outfile)
                        self.write_qs_to_output(encoder, qs, extra_row_fn=extra_row_fn)
                    if progress_monitor:
                        progress_monitor(i + 1, total)


class FlexibleDataExcelExporter(FlexibleDataExporter):
    def __init__(self, slicer: FlexibleDataSlicer, include_charts: bool = True, **kwargs):
        super().__init__(slicer, **kwargs)
        self._seen_sheetnames = set()
        self.include_charts = include_charts
        self.base_fmt_dict = {"font_name": "Arial", "font_size": 9}
        self.base_fmt = None
        self.header_fmt = None
        self.workbook = None

    def stream_data_to_sink(
        self, sink, progress_monitor: Optional[Callable[[int, int], None]] = None
    ):
        from xlsxwriter.workbook import Workbook  # noqa - slow import

        parts = self.slicer.get_parts_queryset() if self.slicer.split_by else None
        # if we have multipart output
        #  - we will monitor on part basis - not on row basis
        #  - we will generate data for the output part by part
        with tempfile.NamedTemporaryFile("wb") as tmp_file:
            workbook = Workbook(tmp_file.name, {"constant_memory": True})
            # store reference to workbook - we may need it in the methods called later
            self.workbook = workbook
            self.base_fmt = workbook.add_format(self.base_fmt_dict)
            self.header_fmt = workbook.add_format({"bold": True, **self.base_fmt_dict})

            # add metadata sheet
            sheet = workbook.add_worksheet("metadata")
            writer = XlsxListWriter(sheet, cell_format=self.base_fmt, header_format=self.header_fmt)
            for _i in range(6):
                # skip some rows - make place for logo
                writer.writerow([])
            self.create_report_metadata(writer)
            writer.finalize()
            sheet.insert_image(
                0,
                0,
                "design/ui/src/assets/celus-dark.png",
                {
                    "x_offset": 30,
                    "y_offset": 20,
                    "url": "https://www.celus.net/",
                    "decorative": True,
                },
            )
            # add the data itself
            if parts is None:
                qs = self.slicer.get_data()
                sheetname = "report"
                sheet = workbook.add_worksheet(sheetname)
                row_count = self.write_qs_to_output(
                    sheet, qs, extra_row_fn=self._remainder_fn(), progress_monitor=progress_monitor
                )
                if self.include_charts and row_count > 0:
                    self.add_chart_sheet(workbook, sheetname, row_count=row_count)
            else:
                total = parts.count()
                self._check_maximum_parts_number(total)
                sheetname_parts = [
                    (
                        self.unique_sheetname(
                            self.column_parts_separator.join(list(self.translate_part_key(part)))
                        ),
                        part,
                    )
                    for part in parts
                ]
                sheetname_parts.sort()
                for i, (sheetname, part) in enumerate(sheetname_parts):
                    if i % 100 == 0:
                        logger.info(f"Exported {i} sheets of {total}")
                    key = [part[name] for name in self.slicer.split_by]
                    qs = self.slicer.get_data(part=key)

                    sheet = workbook.add_worksheet(sheetname)
                    row_count = self.write_qs_to_output(
                        sheet, qs, extra_row_fn=self._remainder_fn(part=key)
                    )
                    self._close_sheet(sheet)
                    if self.include_charts and row_count > 0:
                        self.add_chart_sheet(workbook, sheetname, row_count=row_count)
                    if progress_monitor:
                        progress_monitor(i + 1, total)

            workbook.close()
            self.workbook = None
            with open(tmp_file.name, "rb") as outfile:
                sink.write(outfile.read())

    def create_writer(self, output, fields: List[Tuple[str, str]]) -> DictWriter:
        # format publication date as date (used for items)
        col_formats = {
            "publication_date": self.workbook.add_format(
                {"num_format": "yyyy-mm-dd", **self.base_fmt_dict}
            )
        }
        if "date" in self.slicer.primary_dimensions:
            col_formats["date"] = self.workbook.add_format(
                {"num_format": "yyyy-mm", **self.base_fmt_dict}
            )
        if self.slicer.trend_mode:
            col_formats[self.slicer.COL_REL_DIFF] = self.workbook.add_format(
                {"num_format": "0.00%", **self.base_fmt_dict}
            )

        formulas = self.create_formulas(fields)
        return MappingXlsxDictWriter(
            output,
            fields=fields,
            cell_format=self.base_fmt,
            header_format=self.header_fmt,
            row_formulas=formulas,
            include_col_totals=self.include_col_totals,
            col_formats=col_formats,
            sum_row_skip_cols=self.sum_row_skip_cols(),
        )

    def add_chart_sheet(
        self, workbook: "Workbook", sheetname: str, row_count: int, max_rows_to_show: int = 30
    ):
        sheet = workbook.add_worksheet(self.unique_sheetname("Chart - " + sheetname))
        chart = workbook.add_chart({"type": "bar"})
        chart.set_size({"height": min(900, 150 + row_count * 25), "width": 1024})
        if row_count > max_rows_to_show:
            style = workbook.add_format({"bold": 1, "font_size": 12, "font_name": "Arial"})
            sheet.write(0, 1, f"Chart was limited to first {max_rows_to_show} rows!", style)
            row_count = max_rows_to_show
        # Use the sum_row_skip_cols method which handles multiindex correctly
        skip_cols = self.sum_row_skip_cols()
        if self.include_row_totals:
            skip_cols += 1
        omit_cols = 0  # cols to omit from the chart at the end of the row
        if self.slicer.trend_mode:
            omit_cols += 2
        for i in range(skip_cols, len(self._fields) - omit_cols):
            chart.add_series(
                {
                    "categories": [sheetname, 1, 0, row_count, 0],
                    "values": [sheetname, 1, i, row_count, i],
                    "name": [sheetname, 0, i],
                }
            )
        chart.set_x_axis({"num_font": {"name": "Arial"}})
        # `reverse` means from top to bottom - default is the other way around
        chart.set_y_axis({"reverse": True, "num_font": {"name": "Arial"}})
        chart.set_legend({"font": {"name": "Arial"}})
        # chart.set_title({'name': self.report_name})
        sheet.insert_chart(2, 1, chart)
        self._close_sheet(sheet)

    @classmethod
    def cleanup_sheetname(cls, sheetname: str):
        """
        Ensures that the sheet name does not contain forbidden characters, etc.

        It is context-less, so it cannot check duplicated sheet names - use `unique_sheetname`
        for that.
        """
        for char in r"[]:*?/\\":
            sheetname = sheetname.replace(char, "")
        sheetname = " ".join(sheetname.split())  # normalize whitespace
        sheetname = sheetname.strip("'")
        if len(sheetname) > 31:
            sheetname = sheetname[:30] + "…"
        if sheetname.lower() == "history":
            # history is not allowed as sheet name in Excel
            # (https://xlsxwriter.readthedocs.io/workbook.html)
            sheetname = sheetname + "_"
        if not sheetname:
            return "Sheet"
        return sheetname

    def unique_sheetname(self, sheetname: str, max_len=31):
        """
        Cleans up `sheetname` and the modifies it in a way to ensure it is unique regardless
        of case.
        :param sheetname: the name itself
        :param max_len: the enforced maximum length of the sheet name
        :return:
        """
        assert max_len <= 31, "max in Excel is 31"
        sheetname = self.cleanup_sheetname(sheetname)  # does the preliminary cleanup
        # we leave some space for number if needed; if ' is placed just right, it could end up last
        if len(sheetname) > (max_len - 5):
            sheetname = sheetname[: max_len - 5].rstrip("'") + "…"
        i = 1
        new_sheetname = sheetname
        while new_sheetname.lower() in self._seen_sheetnames:
            new_sheetname = f"{sheetname}-{i}"
            i += 1
        self._seen_sheetnames.add(new_sheetname.lower())
        return new_sheetname

    @classmethod
    def _close_sheet(cls, sheet):
        """
        Closes the sheet to avoid file descriptor limit, see
        https://github.com/jmcnamara/XlsxWriter/issues/58
        for discussion why this is needed and why it is a private method.

        The code is extracted to a method to isolate the workaround
        """
        sheet._opt_close()


class FlexibleDataExcelExporterNoCharts(FlexibleDataExcelExporter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.include_charts = False


format_to_exporter = {
    FileFormat.XLSX: FlexibleDataExcelExporter,
    FileFormat.XLSX_NO_CHARTS: FlexibleDataExcelExporterNoCharts,
    FileFormat.ZIP_CSV: FlexibleDataZipCSVExporter,
}
