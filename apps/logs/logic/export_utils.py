import csv
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Tuple, Union

from xlsxwriter.utility import xl_rowcol_to_cell
from xlsxwriter.worksheet import Worksheet

XSLX_COL_WIDTH_ADJ_RATIO = 0.8  # how to scale column width compared to the computed value
XSLX_COL_WIDTH_ADJ_CONST = 2  # what to add to the scaled column width


def xslx_scale_column_width(width, max_col_width=60):
    return min(int(width * XSLX_COL_WIDTH_ADJ_RATIO) + XSLX_COL_WIDTH_ADJ_CONST, max_col_width)


@dataclass
class Formula:
    key: str  # key of the column where the formula should be written
    refs: List[str]  # keys of the columns to be used in the formula
    operation: str = 'sum'  # function to be applied to the values in refs
    fn: Callable = None  # function to be applied to the values in refs to get the value
    # fn is used to get the correct number in the totals column if the column sum is not the
    # sum of individual values (e.g. when dealing with difference in % or something)


class DictWriter(ABC):
    def __init__(
        self,
        sink,
        fields: List[Tuple[str, str]],
        sum_row_skip_cols: Optional[int] = None,
        row_formulas: Optional[List[Formula]] = None,
        include_col_totals=False,
        **kwargs,
    ):
        self.sink = sink
        self.field_order = []
        self.columns = []
        self.sum_row_skip_cols = sum_row_skip_cols
        self.row_formulas = {}
        for formula in row_formulas or []:
            self.row_formulas[formula.key] = formula
        self.include_col_totals = include_col_totals
        self._column_totals = Counter()
        self._current_row = 0
        for key, column in fields:
            self.field_order.append(key)
            self.columns.append(column)

    @abstractmethod
    def writerow(self, values: dict):
        """
        Mandatory method. Should write one row into the output
        """

    def finalize(self):
        pass

    def apply_formula_fn_to_totals(self, formula: Formula) -> Any:
        values = [self._column_totals[col] for col in formula.refs]
        return formula.fn(*values)


class MappingXlsxDictWriter(DictWriter):
    MAX_COL_WIDTH = 60

    def __init__(
        self,
        sink: Worksheet,
        fields: List[Tuple[str, str]],
        cell_format=None,
        header_format=None,
        col_formats: Optional[dict] = None,
        **kwargs,
    ):
        """
        :param sink:
        :param fields:
        :param cell_format:
        :param header_format:
        :param sum_row_skip_cols: when given as a number, it means that the sum row should be added
               and that it should skip the first n columns (typically the first column is a label
               and should not be summed)
        :param row_formulas: list of formulas to be applied to the corresponding column (key) for
        each row; the `key` must be one of existing fields, refs are indexes of the columns to be
        used in the formula (e.g. [1,2,3]), and the operation is the function to be applied to the
        values in the referenced columns (e.g. 'sum') or a string to be formatted with the ref
        values (e.g. '={0}+{1}').
        :param kwargs:
        """
        super().__init__(sink, fields, **kwargs)
        self.sheet: Worksheet = self.sink  # to make the purpose of the name more obvious
        self.header_format = header_format
        self.cell_format = cell_format
        self._current_row = 0
        self._widths = len(self.columns) * [0]
        self.col_formats = col_formats or {}
        self.writerow_raw(self.columns, format=self.header_format)
        self.sheet.freeze_panes(1, 0)  # freeze the header row

    def formula_to_excel(self, formula: Formula):
        cells = [
            xl_rowcol_to_cell(self._current_row, self.field_order.index(col))
            for col in formula.refs
        ]
        if formula.operation == 'sum':
            return f'=SUM({",".join(cells)})'
        else:
            # the formula may simply be a string which should be filled in with the cell refs
            if '{' in formula.operation:
                try:
                    return formula.operation.format(*cells)
                except IndexError:
                    # the formatting failed, let it fall through to the ValueError
                    pass
            raise ValueError(f'Unknown operation {formula.operation}')

    def writerow(self, values: dict):
        for i, col in enumerate(self.field_order):
            value = values.get(col)
            fmt = self.col_formats.get(col, self.cell_format)
            if formula := self.row_formulas.get(col):
                self.sheet.write_formula(
                    self._current_row,
                    i,
                    self.formula_to_excel(formula),
                    cell_format=fmt,
                    value=value,
                )
            else:
                self.sheet.write(self._current_row, i, value, fmt)
            self._widths[i] = max(self._widths[i], len(str(value)))
            if self.include_col_totals and i >= self.sum_row_skip_cols:
                self._column_totals[col] += value or 0
        self._current_row += 1

    def writerow_raw(self, cells: [Union[str, int]], format=None):
        self.sheet.write_row(row=self._current_row, col=0, data=cells, cell_format=format)
        self._current_row += 1
        for i, cell in enumerate(cells):
            self._widths[i] = max(self._widths[i], len(str(cell)))

    def finalize(self):
        # write the totals row
        if self.include_col_totals and self.sum_row_skip_cols is not None:
            for i, col in enumerate(self.field_order):
                value = ''
                if i == 0:
                    value = 'Total'
                    self.sheet.write(self._current_row, i, value, self.header_format)
                elif i >= self.sum_row_skip_cols:
                    fmt = self.col_formats.get(col, self.header_format)
                    if formula := self.row_formulas.get(col):
                        # if there is a formula assigned to the column, we use it in the totals row
                        # as well
                        if formula.fn:
                            value = self.apply_formula_fn_to_totals(formula)
                        else:
                            value = self._column_totals[col]
                        self.sheet.write_formula(
                            self._current_row,
                            i,
                            self.formula_to_excel(formula),
                            cell_format=fmt,
                            value=value,
                        )
                    else:
                        start = xl_rowcol_to_cell(1, i)
                        end = xl_rowcol_to_cell(self._current_row - 1, i)
                        value = self._column_totals[col]
                        self.sheet.write_formula(
                            self._current_row,
                            i,
                            f'=SUM({start}:{end})',
                            fmt,
                            value=value,
                        )
                # add totals to the widths
                self._widths[i] = max(self._widths[i], len(str(value)))
        # adjust column widths
        for col, width in enumerate(self._widths):
            width = xslx_scale_column_width(width)
            self.sheet.set_column(col, col, width, self.cell_format)


class MappingCSVDictWriter(DictWriter):

    """
    Special DictWriter that maps column names from row keys to different column names
    """

    def __init__(
        self,
        sink,
        fields: List[Tuple[str, str]],
        **kwargs,
    ):
        super().__init__(sink, fields, **kwargs)
        self.writer = csv.writer(self.sink)
        self.writer.writerow(self.columns)

    def writerow(self, values: dict):
        row = []
        for i, col in enumerate(self.field_order):
            value = values.get(col)
            # deal with formulas. We are only interested in formulas which have the `fn` attribute
            # set, as these are the ones that should be computed for each row. If the `fn` is not
            # present, the value stored in the row data is used as-is
            if (formula := self.row_formulas.get(col)) and formula.fn:
                value = formula.fn(*[values.get(ref) for ref in formula.refs])
            if self.include_col_totals and i >= self.sum_row_skip_cols:
                self._column_totals[col] += value or 0
            row.append(value)
        self.writer.writerow(row)

    def finalize(self):
        if self.include_col_totals and self.sum_row_skip_cols is not None:
            row = []
            for i, col in enumerate(self.field_order):
                value = ''
                if i == 0:
                    value = 'Total'
                elif i >= self.sum_row_skip_cols:
                    if (formula := self.row_formulas.get(col)) and formula.fn:
                        # if there is a formula assigned to the column, we use it in the totals row
                        # as well
                        value = self.apply_formula_fn_to_totals(formula)
                    else:
                        value = self._column_totals[col]
                row.append(value)
            self.writer.writerow(row)


class ListWriter(ABC):
    def __init__(self, sink, **kwargs):
        self.sink = sink

    @abstractmethod
    def writerow(self, values: list):
        """
        Mandatory method. Should write one row into the output
        """

    def finalize(self):
        pass


class XlsxListWriter(ListWriter):
    MAX_COL_WIDTH = 60

    def __init__(self, sink: Worksheet, cell_format=None, header_format=None, **kwargs):
        super().__init__(sink, **kwargs)
        self.sheet: Worksheet = self.sink  # add alias for better readability
        self.header_format = header_format
        self.cell_format = cell_format
        self._current_row = 0
        self._widths = 100 * [0]

    def writerow(self, values: list):
        self.sheet.write_row(row=self._current_row, col=0, data=values)
        self._current_row += 1
        for i, cell in enumerate(values[:100]):
            self._widths[i] = max(self._widths[i], len(str(cell)))

    def finalize(self):
        for col, width in enumerate(self._widths):
            if width:
                width = xslx_scale_column_width(width)
                # first column has header_format, other have cell_format
                self.sheet.set_column(
                    col, col, width, self.cell_format if col else self.header_format
                )


class CSVListWriter(ListWriter):

    """
    Special DictWriter that maps column names from row keys to different column names
    """

    def __init__(self, sink, **kwargs):
        super().__init__(sink, **kwargs)
        self.writer = csv.writer(self.sink, **kwargs)

    def writerow(self, values: list):
        self.writer.writerow(values)
