import tempfile

import xlsxwriter
from django.utils import timezone
from logs.logic.export_utils import xslx_scale_column_width
from reporting.logic.computation import Report
from xlsxwriter.utility import xl_rowcol_to_cell


class XlsxExporter:
    def __init__(self, report: Report, include_part_definition: bool = True):
        self.base_fmt = None
        self.header_fmt = None
        self.superheader_fmt = None
        self.report = report
        self.include_part_definition = include_part_definition

    def export(self) -> bytes:
        with tempfile.NamedTemporaryFile('wb') as tmp_file:
            workbook = xlsxwriter.Workbook(tmp_file.name, {'constant_memory': True})
            base_fmt_dict = {'font_name': 'Arial', 'font_size': 9, 'num_format': '#,##0'}
            self.base_fmt = workbook.add_format(base_fmt_dict)
            self.header_fmt = workbook.add_format({'bold': True, **base_fmt_dict})
            self.superheader_fmt = workbook.add_format(
                {'bold': True, 'bg_color': '#d0d0d0', **base_fmt_dict}
            )

            data_row_ranges = []
            sheet_totals = []
            cover_sheet = workbook.add_worksheet('Summary')
            for part, results in self.report.gen_output():
                data_row_range, sheet_total = self.create_part_sheet(workbook, part, results)
                data_row_ranges.append(data_row_range)
                sheet_totals.append(sheet_total)
            self.create_cover_sheet(cover_sheet, data_row_ranges, sheet_totals)
            workbook.close()
            with open(tmp_file.name, 'rb') as outfile:
                return outfile.read()

    def create_cover_sheet(self, sheet, data_row_ranges: [(int, int)], sheet_totals: [int]):
        current_row = 0
        # header
        sheet.write_string(current_row, 0, self.report.name, self.header_fmt)
        current_row += 2  # leave some space
        sheet.write_string(current_row, 0, 'Organization', self.header_fmt)
        sheet.write_string(current_row, 1, self.report.organization.name, self.base_fmt)
        current_row += 1
        sheet.write_string(current_row, 0, 'Covered period', self.header_fmt)
        sheet.write_string(
            current_row, 1, f'{self.report.start_date} - {self.report.end_date}', self.base_fmt
        )
        current_row += 1
        sheet.write_string(current_row, 0, 'Created', self.header_fmt)
        sheet.write_string(
            current_row,
            1,
            timezone.now().astimezone(timezone.get_current_timezone()).strftime('%Y-%m-%d %H:%M'),
            self.base_fmt,
        )

        # data itself
        current_row += 3  # leave some space
        for part, (first_row, last_row), total in zip(
            self.report.parts, data_row_ranges, sheet_totals
        ):
            sheet.write_string(current_row, 0, part.name, self.header_fmt)
            if part.implementation_note:
                sheet.write_comment(current_row, 0, part.implementation_note, {'x_scale': 4})
            sheet.write_string(current_row, 1, part.description, self.base_fmt)
            sheet.write_formula(
                current_row,
                2,
                f"=SUM($'{part.name}'!C{first_row}:C{last_row})",
                self.base_fmt,
                total,
            )
            current_row += 1

        # set column widths
        widths = [
            max(
                len(self.report.name),
                len('Covered period'),
                max(len(part.name) for part in self.report.parts),
            )
            * 1.5,  # 1.4 is a magic number to make it look better,
            max(len(part.description) for part in self.report.parts),
            10,
        ]
        for col, width in enumerate(widths):
            width = xslx_scale_column_width(width, max_col_width=100)
            sheet.set_column(col, col, width, self.base_fmt if col else self.header_fmt)

    def create_part_sheet(self, workbook, part, results) -> ((int, int), int):
        """
        Returns a tuple of tuples: (first_data_row, last_data_row), total)
        """
        sheet = workbook.add_worksheet(part.name)
        current_row = 0
        month_cols = [month.strftime('%Y-%m') for month in self.report.covered_months]
        max_col = len(month_cols) + 3
        # add description if requested
        if self.include_part_definition:
            sheet.write_string(current_row, 0, part.name, self.header_fmt)
            current_row += 1
            sheet.merge_range(current_row, 0, current_row, max_col, part.description, self.base_fmt)
            current_row += 2  # leave some space
            sheet.write_string(current_row, 0, 'Source report', self.header_fmt)
            sheet.write_string(
                current_row, 1, part.primary_source.report_type.short_name, self.base_fmt
            )

            def write_filter(source):
                filters = ', '.join(f'{k}={v}' for k, v in source.filters.items()) or '-'
                sheet.merge_range(
                    current_row,
                    2,
                    current_row,
                    max_col,
                    f'Metric: {source.metric or "*"}; Filters: {filters}',
                    self.base_fmt,
                )

            write_filter(part.primary_source)
            current_row += 1

            if part.fallback_source:
                sheet.write_string(current_row, 0, 'Fallback report', self.header_fmt)
                rep_name = part.fallback_source.report_type.short_name
                if part.subtracted_fallback_source:
                    rep_name += f' - {part.subtracted_fallback_source.report_type.short_name}'
                sheet.write_string(current_row, 1, rep_name, self.base_fmt)
                write_filter(part.fallback_source)
                current_row += 1
            current_row += 2  # leave some space

        # write the header
        header_row = ['Platform', 'Used report', 'Total', *month_cols]
        sheet.write_row(row=current_row, col=0, data=header_row, cell_format=self.superheader_fmt)
        current_row += 1
        # at least 7 chars per column
        widths = [max(len(str(cell)), 7) for cell in header_row]

        # write the data
        # we need to write formulas into total column
        total = 0
        first_data_row = current_row + 1  # +1 because of different indexing
        for rec in results:
            # primary obj name
            sheet.write_string(current_row, 0, rec.primary_obj.name, self.header_fmt)
            widths[0] = max(widths[0], len(rec.primary_obj.name))
            # used report type
            rt_name = rec.used_report_type.short_name if rec.used_report_type else ''
            sheet.write_string(current_row, 1, rt_name, self.base_fmt)
            widths[1] = max(widths[1], len(rt_name))
            # total as formula
            start = xl_rowcol_to_cell(current_row, 3)
            end = xl_rowcol_to_cell(current_row, 3 + len(self.report.covered_months) - 1)
            sheet.write_formula(current_row, 2, f'=SUM({start}:{end})', self.base_fmt, rec.total)
            widths[2] = max(widths[2], len(str(rec.total)) + 1)  # +1 for extra space
            # monthly data
            for i, month in enumerate(self.report.covered_months):
                sheet.write_number(current_row, i + 3, rec.monthly_data[month], self.base_fmt)
                widths[i + 3] = max(widths[i + 3], len(str(rec.monthly_data[month])))
            current_row += 1
            total += rec.total

        for col, width in enumerate(widths):
            if width:
                width = xslx_scale_column_width(width)
                # first column has header_format, other have cell_format
                sheet.set_column(col, col, width, self.base_fmt if col else self.header_fmt)
        return (first_data_row, current_row), total
