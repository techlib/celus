import tempfile
from typing import Dict, List, Optional, Tuple, Union

from django.utils import timezone
from logs.logic.export_utils import xslx_scale_column_width

from reporting.logic.computation import Report, ReportPart, ReportPartStage, ResultRow


class XlsxExporter:
    tab_palette = [
        "#4CAF50",
        "#3F51B5",
        "#9C27B0",
        "#E91E63",
        "#607D8B",
        "#FF9800",
        "#8BC34A",
        "#009688",
    ]

    base_fmt_dict = {"font_name": "Arial", "font_size": 9, "num_format": "#,##0"}

    data_col_shift = 3  # how many columns there are in the output before the month columns

    def __init__(self, report: Report, include_part_definition: bool = True):
        self.base_fmt = None
        self.header_fmt = None
        self.superheader_fmt = None
        self.empty_data_fmt = None
        self.report = report
        self.include_part_definition = include_part_definition
        self.report_output = None
        self.workbook = None
        self.sheet_names: Dict[Tuple[str, str], str] = {}  # key will be (part_name, stage_name)
        self.sheet_first_row: Dict[str, int] = {}  # key will be sheet name

    @classmethod
    def sanitize_sheet_name(cls, name: str) -> str:
        return name.replace("/", "|")[:31]

    def export(self) -> bytes:
        import xlsxwriter

        with tempfile.NamedTemporaryFile("wb") as tmp_file:
            self.workbook = xlsxwriter.Workbook(tmp_file.name, {"constant_memory": True})
            self.base_fmt = self.workbook.add_format(self.base_fmt_dict)
            self.empty_data_fmt = self.workbook.add_format(
                {"font_color": "#888888", **self.base_fmt_dict}
            )
            self.header_fmt = self.workbook.add_format({"bold": True, **self.base_fmt_dict})
            self.superheader_fmt = self.workbook.add_format(
                {"bold": True, "bg_color": "#d0d0d0", **self.base_fmt_dict}
            )

            cover_sheet = self.workbook.add_worksheet("Summary")
            self.report_output = self.report.get_output()
            for part_idx, part in enumerate(self.report.parts):
                results = self.report_output[part.name]
                tab_color = self.tab_palette[part_idx % len(self.tab_palette)]
                for i, stage in enumerate(part.stages):
                    self.report.context.set_current_part(part.name)
                    self.create_stage_sheet(
                        part, stage, results["stages"][i]["data"], tab_color=tab_color
                    )
            self.create_cover_sheet(cover_sheet)
            self.workbook.close()
            with open(tmp_file.name, "rb") as outfile:
                return outfile.read()

    def create_cover_sheet(self, sheet):
        current_row = 0
        # header
        context = self.report.context
        sheet.write_string(current_row, 0, self.report.name, self.header_fmt)
        current_row += 2  # leave some space
        sheet.write_string(current_row, 0, "Organization", self.header_fmt)
        sheet.write_string(current_row, 1, context.organization.name, self.base_fmt)
        current_row += 1
        sheet.write_string(current_row, 0, "Covered period", self.header_fmt)
        sheet.write_string(
            current_row, 1, f"{context.start_date} - {context.end_date}", self.base_fmt
        )
        current_row += 1
        sheet.write_string(current_row, 0, "Created", self.header_fmt)
        sheet.write_string(
            current_row,
            1,
            timezone.now().astimezone(timezone.get_current_timezone()).strftime("%Y-%m-%d %H:%M"),
            self.base_fmt,
        )

        # data itself
        current_row += 3  # leave some space
        for i, part in enumerate(self.report.parts):
            # for each part, we use the last stage as this should be the one with the final data
            color = self.tab_palette[i % len(self.tab_palette)]
            bg_format = self.workbook.add_format(
                {"bg_color": color, "font_color": "#ffffff", "bold": True, **self.base_fmt_dict}
            )
            stage = part.stages[-1]
            sheet_name = self.sheet_names[(part.name, stage.name)]
            first_row = self.sheet_first_row[sheet_name]
            stage_data = self.report_output[part.name]["stages"][-1]["data"]
            last_row = first_row + len(stage_data) - 1
            total = sum(row.total for row in stage_data)
            sheet.write_string(current_row, 0, part.name, bg_format)
            if part.implementation_note:
                sheet.write_comment(current_row, 0, part.implementation_note, {"x_scale": 4})
            sheet.write_string(current_row, 1, part.description, self.base_fmt)
            sheet.write_formula(
                current_row,
                2,
                f"=SUM('{sheet_name}'!C{first_row}:C{last_row})",
                self.base_fmt,
                total,
            )
            current_row += 1

        # set column widths
        widths = [
            max(
                len(self.report.name),
                len("Covered period"),
                max(len(part.name) for part in self.report.parts),
            )
            * 1.5,  # 1.5 is a magic number to make it look better,
            max(len(part.description) for part in self.report.parts),
            10,
        ]
        for col, width in enumerate(widths):
            width = xslx_scale_column_width(width, max_col_width=100)
            sheet.set_column(col, col, width, self.base_fmt if col else self.header_fmt)

    def create_stage_sheet(
        self, part: ReportPart, stage: ReportPartStage, results: [ResultRow], tab_color=None
    ) -> None:
        from xlsxwriter.utility import xl_rowcol_to_cell  # noqa - slow import

        # if the part has the same name as the stage, we don't want to repeat it in the sheet name
        sheet_name = self.sanitize_sheet_name(
            f"{part.name} ({stage.name})" if part.name != stage.name else stage.name
        )
        self.sheet_names[(part.name, stage.name)] = sheet_name
        sheet = self.workbook.add_worksheet(sheet_name)
        if tab_color:
            sheet.set_tab_color(tab_color)
        current_row = 0
        covered_months = self.report.context.covered_months
        month_cols = [month.strftime("%Y-%m") for month in covered_months]
        max_col = len(month_cols) + 3
        # add description if requested
        if self.include_part_definition:
            sheet.write_string(current_row, 0, part.name, self.header_fmt)
            current_row += 1
            sheet.merge_range(current_row, 0, current_row, max_col, part.description, self.base_fmt)
            current_row += 2  # leave some space
            for source_id in stage.get_used_data_sources():
                source = self.report.get_source(source_id)
                report_title = "Source report" if not source.fallback_for else "Fallback report"
                sheet.write_string(current_row, 0, report_title, self.header_fmt)
                sheet.write_string(current_row, 1, source.name, self.base_fmt)
                # write description of the filters
                filters = ", ".join(f"{k}={v}" for k, v in source.filters.items()) or "-"
                sheet.merge_range(
                    current_row,
                    2,
                    current_row,
                    max_col,
                    f"Metric: {source.metric or '*'}; Filters: {filters}",
                    self.base_fmt,
                )
                current_row += 1

            current_row += 2  # leave some space

        # write the header
        header_row = ["Platform", "Used report", "Total", *month_cols]
        sheet.write_row(row=current_row, col=0, data=header_row, cell_format=self.superheader_fmt)
        current_row += 1
        # at least 7 chars per column
        widths = [max(len(str(cell)), 7) for cell in header_row]

        # write the data
        # we need to write formulas into total column
        total = 0
        first_data_row = current_row + 1  # +1 because of different indexing
        self.sheet_first_row[sheet_name] = first_data_row

        for rec_idx, rec in enumerate(results):
            # primary obj name
            sheet.write_string(current_row, 0, rec.primary_obj.name, self.header_fmt)
            widths[0] = max(widths[0], len(rec.primary_obj.name))
            # used report type
            sheet.write_string(current_row, 1, rec.source_name, self.base_fmt)
            widths[1] = max(widths[1], len(rec.source_name))
            # total as formula
            start = xl_rowcol_to_cell(current_row, 3)
            end = xl_rowcol_to_cell(current_row, 3 + len(covered_months) - 1)
            sheet.write_formula(current_row, 2, f"=SUM({start}:{end})", self.base_fmt, rec.total)
            widths[2] = max(widths[2], len(str(rec.total)) + 1)  # +1 for extra space
            # monthly data
            for i, month in enumerate(covered_months):
                formula, _sheet = self.construct_formula(
                    stage.parsed_formula, i, rec_idx, current_row, part
                )
                if formula:
                    sheet.write_formula(
                        current_row,
                        i + self.data_col_shift,
                        formula,
                        self.base_fmt,
                        rec.monthly_data[month],
                    )
                else:
                    sheet.write_number(
                        current_row, i + self.data_col_shift, rec.monthly_data[month], self.base_fmt
                    )
                widths[i + 3] = max(widths[i + 3], len(str(rec.monthly_data[month])))
            current_row += 1
            total += rec.total

        for col, width in enumerate(widths):
            if width:
                width = xslx_scale_column_width(width)
                # first column has header_format, other have cell_format
                sheet.set_column(col, col, width, self.base_fmt if col else self.header_fmt)
        # apply conditional formatting
        for row in range(first_data_row - 1, current_row):
            sheet.conditional_format(
                f"{xl_rowcol_to_cell(row, 0)}:{xl_rowcol_to_cell(row, len(widths) - 1)}",
                {
                    "type": "formula",
                    "criteria": f"={xl_rowcol_to_cell(row, 2, True, True)}=0",
                    "format": self.empty_data_fmt,
                },
            )

    def construct_formula(
        self,
        parsed_formula: List[Union[str, list]],
        col: int,
        row: int,
        current_row: int,
        part: ReportPart,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        :param parsed_formula: parsed formula
        :param col: column index in the data DataFrame
        :param row: row index in the data DataFrame
        :param current_row: row index in the output sheet
        :param part: current part
        Return a tuple of (formula, sheet_name) for a given cell. Where both are None if
        the cell is not a formula but a simple value.
        """
        from xlsxwriter.utility import xl_rowcol_to_cell  # noqa - slow import

        context_args = (col, row, current_row, part)
        if len(parsed_formula) == 1:
            variable = parsed_formula[0]
            if isinstance(variable, list):
                return self.construct_formula(variable, *context_args)
            if stage_ref := self.report.context.get_stage_for_current_part(variable):
                stage_sheet = self.sheet_names[(part.name, stage_ref.name)]
                fr = self.sheet_first_row[stage_sheet]
                # -1 because of different indexing
                cell = xl_rowcol_to_cell(fr + row - 1, col + self.data_col_shift)
                return f"'{stage_sheet}'!{cell}", stage_sheet
            if self.report.sources_by_id.get(variable):
                # when directly accessing source, we just use the value - no formula needed
                return None, None
            raise ValueError(f"Unknown variable: {variable}")
        if len(parsed_formula) == 3:
            left, op, right = parsed_formula
            left_data, left_sheet = self.construct_formula([left], *context_args)
            right_data, right_sheet = self.construct_formula([right], *context_args)
            if left_data is None and right_data is None:
                # if both subexpressions are not formulas, the result is not a formula either
                return None, None
            if left_data is None or right_data is None:
                raise ValueError(
                    f"Mixing raw source data and stage data in a formula is not supported: "
                    f"{parsed_formula}"
                )
            if op == "|":
                if left_sheet:
                    left_fr = self.sheet_first_row[left_sheet]
                    source_ref_col = xl_rowcol_to_cell(left_fr + row - 1, 1)
                    # Note: the following way of deciding which source sheet to use is not
                    # perfect. A disadvantage is that when the user adds data into the left
                    # source sheet, thus making it the preferred one, the right sheet will
                    # still be used because the decision is made based on the shown
                    # `source_name`. So the user will have to manually change the `source_name`
                    # next to this cell to make the right sheet be used.
                    #
                    # A possible alternative would be to use the `total` value for the decision.
                    # But this would mean that when the user adds data into the left source
                    # sheet, the total would be correctly updated. But the reference to the
                    # source in `source_name` would remain the same, which would be confusing.
                    #
                    # The best solution would be to use the `total` value for the decision, and
                    # make the `source_name` dynamic as well. But this would require a lot of
                    # changes in the code, and as this all is really a corner case, it's not
                    # worth the effort. At least for now.
                    return (
                        f"IF('{left_sheet}'!{source_ref_col}=B{current_row + 1}, "
                        f"{left_data}, {right_data})"
                    ), None
                elif right_sheet:
                    # if we got here, the left side is a formula of stages and the right side
                    # is a plain stage reference. So we will use the right side as the
                    # reference.
                    right_fr = self.sheet_first_row[right_sheet]
                    source_ref_col = xl_rowcol_to_cell(right_fr + row - 1, 1)
                    return (
                        f"IF('{right_sheet}'!{source_ref_col}=B{current_row + 1}, "
                        f"{right_data}, {left_data})"
                    ), None
                else:
                    # both sides are formulas of stages, which we do not support
                    # Note: a simple fix would be to return None, None and the caller would
                    # just use the numerical values and not a formula. But this would mean
                    # that we will break the connection between the previous stages and this
                    # one, and the sheets would not be updated when the previous stages are
                    # changed. So we just raise an error instead.
                    raise ValueError(
                        "Using two formulas of stages with the '|' operator is not supported:"
                        f" {parsed_formula}"
                    )
            if op == "-":
                return f"{left_data} - {right_data}", None
            if op == "+":
                return f"{left_data} + {right_data}", None
            raise ValueError(f"Unsupported operator: {op}")
        raise ValueError(f"Unsupported formula: {parsed_formula}")
