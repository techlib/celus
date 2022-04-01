import codecs
import tempfile
from abc import ABC, abstractmethod
from typing import Optional, Callable, Type, Tuple, Any, Union
from zipfile import ZipFile, ZIP_DEFLATED

import xlsxwriter
from django.conf import settings
from django.db.models import Model, ForeignKey, Field
from django.db.models.base import ModelBase
from django.utils.text import slugify
from django.utils.timezone import now
from django.utils.translation import gettext as _
from mptt.models import MPTTModelBase

from logs.logic.export_utils import (
    XlsxListWriter,
    MappingXlsxDictWriter,
    CSVListWriter,
    MappingCSVDictWriter,
    DictWriter,
    ListWriter,
)
from logs.logic.reporting.slicer import FlexibleDataSlicer
from logs.models import DimensionText, ReportType, AccessLog
from organizations.models import Organization


class FlexibleDataExporter(ABC):

    object_remapped_dims = {'target': {'columns': ['name', 'issn', 'eissn', 'isbn']}}

    def __init__(
        self,
        slicer: FlexibleDataSlicer,
        column_parts_separator: str = ' / ',
        report_name: str = '',
        report_owner=None,
    ):
        self.slicer = slicer
        self.report_name = report_name
        self.report_owner = report_owner

        self.involved_report_types = self.slicer.involved_report_types()
        self.column_parts_separator = column_parts_separator
        self.explicit_prim_dim, self.remapped_prim_dim, prim_dim = self.resolve_dimension(
            self.slicer.primary_dimension
        )
        # how the primary dimension is called in the query output
        self.prim_dim_key = self.slicer.primary_dimension
        if self.remapped_prim_dim:
            if self.explicit_prim_dim:
                self.prim_dim_remap = {
                    obj['pk']: obj['text']
                    for obj in DimensionText.objects.filter(dimension=prim_dim).values('pk', 'text')
                }
            else:
                self.prim_dim_remap = {
                    obj['pk']: obj
                    for obj in prim_dim.objects.all().values('pk', *self.remapped_keys())
                }
                self.prim_dim_key = 'pk'
        else:
            self.prim_dim_remap = {}
        self._fields = []

    def remapped_keys(self):
        return self.object_remapped_dims.get(self.slicer.primary_dimension, {}).get(
            'columns', ['name']
        )

    @abstractmethod
    def stream_data_to_sink(
        self, sink, progress_monitor: Optional[Callable[[int, int], None]] = None,
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
        self, output, qs, progress_monitor: Optional[Callable[[int, int], None]] = None, **kwargs,
    ) -> int:
        """
        `kwargs` will be passed to the writer
        """
        total = 0
        if progress_monitor:
            # we put out the total as soon as possible
            total = qs.count()
            progress_monitor(0, total)
        data = qs.iterator()
        try:
            row = next(data)
        except StopIteration:
            return 0
        fields = [(self.prim_dim_key, self.primary_column_name())]
        # possible other remapped attrs of primary object
        remap_keys = self.remapped_keys()
        for key in remap_keys[1:]:
            fields.append((key, key.upper()))
        # fields from groups
        other_fields = []
        for key in row:
            if key.startswith('grp-'):
                other_fields.append((key, self.remap_column_name(key)))
        # sort columns by their remapped name
        other_fields.sort(key=lambda x: (x[1], x[0]))
        fields += other_fields
        self._fields = fields
        writer = self.create_writer(output, fields)
        self.writerow(writer, row)
        count = 1
        for i, row in enumerate(data):
            self.writerow(writer, row)
            count += 1
            if progress_monitor and count % 100 == 0:
                progress_monitor(count, total)
        if progress_monitor:
            progress_monitor(total, total)
        writer.finalize()
        return count

    def writerow(self, writer, row):
        if self.remapped_prim_dim:
            if self.explicit_prim_dim:
                # remap to text using the DimensionText mapping - mapper converts directly to text
                row[self.prim_dim_key] = self.prim_dim_remap.get(
                    row[self.prim_dim_key], row[self.prim_dim_key]
                )
            else:
                # mapper converts to dict
                remap_data = self.prim_dim_remap.get(row[self.prim_dim_key], {})
                # remap the first column
                remap_keys = self.remapped_keys()
                row[self.prim_dim_key] = remap_data.get(remap_keys[0], row[self.prim_dim_key])
                for key in remap_keys[1:]:
                    # remap all other keys
                    row[key] = remap_data.get(key, '')
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

    def primary_column_name(self) -> str:
        return self.dimension_output_name(self.slicer.primary_dimension)

    def dimension_output_name(self, dim_name: str) -> str:
        explicit, _remapped, dim_model = self.resolve_dimension(dim_name)
        if explicit:
            return dim_model.name or dim_model.short_name
        if isinstance(dim_model, (ModelBase, MPTTModelBase)):
            return str(dim_model._meta.verbose_name)
        # dim_model must be a Field, but let's make sure
        if isinstance(dim_model, Field):
            return str(dim_model.verbose_name)
        raise ValueError(f'Could not resolve dimension: {dim_name}')

    def dimension_remap(self, dimension, value):
        if value is None:
            return '-'
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
            return False, True, field.remote_field.model
        elif ref.startswith('dim'):
            # we need the report types to deal with this
            if len(self.involved_report_types) != 1:
                raise ValueError(
                    'Exactly one report type should be active when resolving explicit dimensions'
                )
            rt: ReportType = self.involved_report_types[0]
            dim = rt.dimension_by_attr_name(ref)
            return True, dim.type == dim.TYPE_TEXT, dim
        else:
            return False, False, field

    def create_report_metadata(self, writer: ListWriter):
        writer.writerow([_('Report name'), self.report_name])
        writer.writerow([_('Created'), str(now())])
        writer.writerow([_('Created for'), str(self.report_owner)])
        writer.writerow([_('Celus version'), str(settings.CELUS_VERSION)])
        writer.writerow(['', ''])
        writer.writerow(
            [
                _('Split by'),
                ', '.join(self.dimension_output_name(dim) for dim in self.slicer.split_by)
                if self.slicer.split_by
                else '-',
            ]
        )
        writer.writerow([_('Rows'), self.primary_column_name()])
        writer.writerow(
            [
                _('Columns'),
                str('; '.join(self.dimension_output_name(dim) for dim in self.slicer.group_by)),
            ]
        )
        for i, fltr in enumerate(self.slicer.dimension_filters):
            writer.writerow(
                [_('Applied filters') if i == 0 else '', self.slicer.filter_to_str(fltr)]
            )
        # print out organizations for which the report was created in case they would be "hidden"
        # (not present in rows, cols, split_by or filter)
        dim = 'organization'
        if (
            self.slicer.primary_dimension != dim
            and dim not in self.slicer.split_by
            and dim not in self.slicer.group_by
            and not any(f.dimension == dim for f in self.slicer.dimension_filters)
        ):
            writer.writerow([])
            writer.writerow(
                [
                    _('Included organizations'),
                    _(
                        '(No organization filter was applied, the data represent the following '
                        'organizations)'
                    ),
                ],
            )
            if self.slicer.organization_filter:
                # if an explicit filter was applied, use it
                orgs = self.slicer.organization_filter
            elif self.report_owner:
                # otherwise, use what user has access to
                orgs = self.report_owner.accessible_organizations
            else:
                # if nothing is available, ask the slicer itself
                orgs = Organization.objects.filter(
                    pk__in=[
                        rec['organization']
                        for rec in self.slicer.get_possible_dimension_values_queryset(
                            'organization'
                        )
                    ]
                )
            for org in orgs.order_by('name'):
                writer.writerow(['', org.name])


class FlexibleDataSimpleCSVExporter(FlexibleDataExporter):

    """
    Simple CSV output exporter which does not support multi-part output and/or metadata output
    """

    def remapped_keys(self):
        return self.object_remapped_dims.get(self.slicer.primary_dimension, {}).get(
            'columns', ['name']
        )

    def stream_data_to_sink(
        self, sink, progress_monitor: Optional[Callable[[int, int], None]] = None,
    ) -> int:
        qs = self.slicer.get_data()
        self.write_qs_to_output(sink, qs, progress_monitor=progress_monitor)

    def create_writer(self, output, fields: list) -> DictWriter:
        return MappingCSVDictWriter(output, fields=fields)


class FlexibleDataZipCSVExporter(FlexibleDataExporter):

    """
    Exporter creating zipped CSV files with support for metadata and multi-part output
    """

    def stream_data_to_sink(
        self, sink, progress_monitor: Optional[Callable[[int, int], None]] = None,
    ) -> int:
        parts = self.slicer.get_parts_queryset() if self.slicer.split_by else None
        with ZipFile(sink, 'w', compression=ZIP_DEFLATED) as outzip:
            # add metadata sheet
            with outzip.open('_metadata.csv', 'w', force_zip64=True) as outfile:
                encoder = codecs.getwriter('utf-8')(outfile)
                writer = CSVListWriter(encoder)
                self.create_report_metadata(writer)
                writer.finalize()

            # output data itself
            if parts is None:
                qs = self.slicer.get_data()
                fname = "report"
                with outzip.open(fname + '.csv', 'w', force_zip64=True) as outfile:
                    writer = codecs.getwriter('utf-8')
                    encoder = writer(outfile)
                    self.write_qs_to_output(encoder, qs, progress_monitor=progress_monitor)
            else:
                total = parts.count()
                for i, part in enumerate(parts):
                    key = [part[name] for name in self.slicer.split_by]
                    qs = self.slicer.get_data(part=key)
                    fname = "-".join([slugify(p) for p in self.translate_part_key(part)])
                    with outzip.open(fname + '.csv', 'w', force_zip64=True) as outfile:
                        writer = codecs.getwriter('utf-8')
                        encoder = writer(outfile)
                        self.write_qs_to_output(encoder, qs)
                    if progress_monitor:
                        progress_monitor(i + 1, total)

    def create_writer(self, output, fields: list) -> DictWriter:
        return MappingCSVDictWriter(output, fields=fields)


class FlexibleDataExcelExporter(FlexibleDataExporter):

    object_remapped_dims = {'target': {'columns': ['name', 'issn', 'eissn', 'isbn']}}

    def __init__(
        self,
        slicer: FlexibleDataSlicer,
        column_parts_separator: str = ' / ',
        report_name: str = '',
        report_owner=None,
    ):
        super().__init__(
            slicer,
            column_parts_separator=column_parts_separator,
            report_name=report_name,
            report_owner=report_owner,
        )
        self._seen_sheetnames = set()
        self.base_fmt = None
        self.header_fmt = None

    def stream_data_to_sink(
        self, sink, progress_monitor: Optional[Callable[[int, int], None]] = None,
    ) -> int:
        parts = self.slicer.get_parts_queryset() if self.slicer.split_by else None
        # if we have multi-part output
        #  - we will monitor on part basis - not on row basis
        #  - we will generate data for the output part by part
        with tempfile.NamedTemporaryFile('wb') as tmp_file:
            workbook = xlsxwriter.Workbook(tmp_file.name)
            base_fmt_dict = {'font_name': 'Arial', 'font_size': 9}  # , 'num_format': '#,##0'}
            self.base_fmt = workbook.add_format(base_fmt_dict)
            self.header_fmt = workbook.add_format({'bold': True, **base_fmt_dict})

            # add metadata sheet
            sheet = workbook.add_worksheet("metadata")
            writer = XlsxListWriter(sheet, cell_format=self.base_fmt, header_format=self.header_fmt)
            for i in range(6):
                # skip some rows - make place for logo
                writer.writerow([])
            self.create_report_metadata(writer)
            writer.finalize()
            sheet.insert_image(
                0,
                0,
                'design/ui/src/assets/celus-dark.png',
                {
                    'x_offset': 30,
                    'y_offset': 20,
                    'url': 'https://www.celus.net/',
                    'decorative': True,
                },
            )

            # add the data itself
            if parts is None:
                qs = self.slicer.get_data()
                sheetname = "report"
                sheet = workbook.add_worksheet(sheetname)
                self.write_qs_to_output(
                    sheet, qs, progress_monitor=progress_monitor,
                )
                self.add_chart_sheet(workbook, sheetname, row_count=qs.count())
            else:
                total = parts.count()
                sheetname_parts = [
                    (
                        self.unique_sheetname(
                            self.column_parts_separator.join(
                                [p for p in self.translate_part_key(part)]
                            )
                        ),
                        part,
                    )
                    for part in parts
                ]
                sheetname_parts.sort()
                for i, (sheetname, part) in enumerate(sheetname_parts):
                    key = [part[name] for name in self.slicer.split_by]
                    qs = self.slicer.get_data(part=key)
                    sheet = workbook.add_worksheet(sheetname)
                    self.write_qs_to_output(sheet, qs)
                    self.add_chart_sheet(workbook, sheetname, row_count=qs.count())
                    if progress_monitor:
                        progress_monitor(i + 1, total)

            workbook.close()
            with open(tmp_file.name, 'rb') as outfile:
                sink.write(outfile.read())

    def create_writer(self, output, fields: list) -> DictWriter:
        return MappingXlsxDictWriter(
            output, fields=fields, cell_format=self.base_fmt, header_format=self.header_fmt
        )

    def add_chart_sheet(
        self,
        workbook: xlsxwriter.Workbook,
        sheetname: str,
        row_count: int,
        max_rows_to_show: int = 30,
    ):
        sheet = workbook.add_worksheet(self.unique_sheetname('Chart - ' + sheetname))
        chart = workbook.add_chart({'type': 'bar'})
        chart.set_size({'height': min(900, 150 + row_count * 25), 'width': 1024})
        if row_count > max_rows_to_show:
            style = workbook.add_format({'bold': 1, 'font_size': 12, 'font_name': 'Arial'})
            sheet.write(0, 1, f'Chart was limited to first {max_rows_to_show} rows!', style)
            row_count = max_rows_to_show
        skip_cols = len(self.remapped_keys())  # for titles skip ISSN and other cols
        for i in range(skip_cols, len(self._fields)):
            chart.add_series(
                {
                    'categories': [sheetname, 1, 0, row_count, 0],
                    'values': [sheetname, 1, i, row_count, i],
                    'name': [sheetname, 0, i],
                }
            )
        chart.set_x_axis({'num_font': {'name': 'Arial'}})
        # `reverse` means from top to bottom - default is the other way around
        chart.set_y_axis({'reverse': True, 'num_font': {'name': 'Arial'}})
        chart.set_legend({'font': {'name': 'Arial'}})
        # chart.set_title({'name': self.report_name})
        sheet.insert_chart(2, 1, chart)

    @classmethod
    def cleanup_sheetname(cls, sheetname: str):
        """
        Ensures that the sheet name does not contain forbidden characters, etc.

        It is context-less, so it cannot check duplicated sheet names - use `unique_sheetname`
        for that.
        """
        for char in r'[]:*?/\\':
            sheetname = sheetname.replace(char, '')
        sheetname = ' '.join(sheetname.split())  # normalize whitespace
        sheetname = sheetname.strip("'")
        if len(sheetname) > 31:
            sheetname = sheetname[:30] + '…'
        if sheetname.lower() == 'history':
            # history is not allowed as sheet name in Excel
            # (https://xlsxwriter.readthedocs.io/workbook.html)
            sheetname = sheetname + '_'
        if not sheetname:
            return 'Sheet'
        return sheetname

    def unique_sheetname(self, sheetname: str, max_len=31):
        """
        Cleans up `sheetname` and the modifies it in a way to ensure it is unique regardless
        of case.
        :param sheetname: the name itself
        :param max_len: the enforced maximum length of the sheet name
        :return:
        """
        assert max_len <= 31, 'max in Excel is 31'
        sheetname = self.cleanup_sheetname(sheetname)  # does the preliminary cleanup
        # we leave some space for number if needed; if ' is placed just right, it could end up last
        if len(sheetname) > (max_len - 5):
            sheetname = sheetname[: max_len - 5].rstrip("'") + '…'
        i = 1
        new_sheetname = sheetname
        while new_sheetname.lower() in self._seen_sheetnames:
            new_sheetname = f'{sheetname}-{i}'
            i += 1
        self._seen_sheetnames.add(new_sheetname.lower())
        return new_sheetname
