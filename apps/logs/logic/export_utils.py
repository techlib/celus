import csv
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union

from xlsxwriter.utility import xl_rowcol_to_cell
from xlsxwriter.worksheet import Worksheet

XSLX_COL_WIDTH_ADJ_RATIO = 0.75  # how to scale column width compared to the computed value
XSLX_COL_WIDTH_ADJ_CONST = 2  # what to add to the scaled column width


def xslx_scale_column_width(width, max_col_width=60):
    return min(int(width * XSLX_COL_WIDTH_ADJ_RATIO) + XSLX_COL_WIDTH_ADJ_CONST, max_col_width)


class DictWriter(ABC):
    def __init__(self, sink, fields: List[Tuple[str, str]], **kwargs):
        self.sink = sink
        self.field_order = []
        self.columns = []
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


class MappingXlsxDictWriter(DictWriter):
    MAX_COL_WIDTH = 60

    @dataclass
    class Formula:
        key: str  # key of the column where the formula should be written
        refs: List[str]  # keys of the columns to be used in the formula
        operation: str = 'sum'  # function to be applied to the values in refs

    def __init__(
        self,
        sink: Worksheet,
        fields: List[Tuple[str, str]],
        cell_format=None,
        header_format=None,
        sum_row_skip_cols: Optional[int] = None,
        row_formulas: Optional[List[Formula]] = None,
        **kwargs,
    ):
        """
        :param sink:
        :param fields:
        :param cell_format:
        :param header_format:
        :param sum_row_skip_cols: when given as a number, it means that a sum row should be added
        just below the header row, and the sum row should skip the first n columns
        :param row_formulas: list of formulas to be applied to the corresponding column (key) for
        each row; the `key` must be one of existing fields, refs are indexes of the columns to be
        used in the formula (e.g. [1,2,3]), and the operation is the function to be applied to the
        values in the referenced columns (e.g. 'sum')
        :param kwargs:
        """
        super().__init__(sink, fields, **kwargs)
        self.sheet: Worksheet = self.sink  # to make the purpose of the name more obvious
        self.header_format = header_format
        self.cell_format = cell_format
        self.sum_row_skip_cols = sum_row_skip_cols
        self._current_row = 0
        self._widths = len(self.columns) * [0]
        self.row_formulas = {}
        for formula in row_formulas or []:
            self.row_formulas[formula.key] = formula
        self.writerow_raw(self.columns, format=self.header_format)
        self.sheet.freeze_panes(1, 0)  # freeze the header row
        self._column_totals = Counter()

    def formula_to_excel(self, formula: Formula):
        if formula.operation == 'sum':
            cells = [
                xl_rowcol_to_cell(self._current_row, self.field_order.index(col))
                for col in formula.refs
            ]
            return f'=SUM({",".join(cells)})'
        else:
            raise ValueError(f'Unknown operation {formula.operation}')

    def writerow(self, values: dict):
        for i, col in enumerate(self.field_order):
            value = values.get(col)
            if formula := self.row_formulas.get(col):
                self.sheet.write_formula(
                    self._current_row,
                    i,
                    self.formula_to_excel(formula),
                    cell_format=self.cell_format,
                    value=value,
                )
            else:
                self.sheet.write(self._current_row, i, value, self.cell_format)
            self._widths[i] = max(self._widths[i], len(str(value)))
            if i >= self.sum_row_skip_cols:
                self._column_totals[col] += value
        self._current_row += 1

    def writerow_raw(self, cells: [Union[str, int]], format=None):
        self.sheet.write_row(row=self._current_row, col=0, data=cells, cell_format=format)
        self._current_row += 1
        for i, cell in enumerate(cells):
            self._widths[i] = max(self._widths[i], len(str(cell)))

    def finalize(self):
        # write the totals row
        if self.sum_row_skip_cols is not None:
            for i, col in enumerate(self.field_order):
                if i == 0:
                    self.sheet.write(self._current_row, i, 'Total', self.header_format)
                elif i >= self.sum_row_skip_cols:
                    start = xl_rowcol_to_cell(1, i)
                    end = xl_rowcol_to_cell(self._current_row - 1, i)
                    self.sheet.write_formula(
                        self._current_row,
                        i,
                        f'=SUM({start}:{end})',
                        self.header_format,
                        value=self._column_totals[col],
                    )
        # adjust column widths
        for col, width in enumerate(self._widths):
            width = xslx_scale_column_width(width)
            self.sheet.set_column(col, col, width, self.cell_format)


class MappingCSVDictWriter(DictWriter):

    """
    Special DictWriter that maps column names from row keys to different column names
    """

    def __init__(self, sink, fields: List[Tuple[str, str]], **kwargs):
        super().__init__(sink, fields, **kwargs)
        self.writer = csv.writer(self.sink, **kwargs)
        self.writer.writerow(self.columns)

    def writerow(self, values: dict):
        row = [values.get(col) for col in self.field_order]
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
