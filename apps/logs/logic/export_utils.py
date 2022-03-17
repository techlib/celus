import csv
from abc import ABC, abstractmethod
from typing import Tuple, List, Union

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

    def __init__(
        self,
        sink: Worksheet,
        fields: List[Tuple[str, str]],
        cell_format=None,
        header_format=None,
        **kwargs,
    ):
        super().__init__(sink, fields, **kwargs)
        self.sheet: Worksheet = self.sink  # to make the purpose of the name more obvious
        self.header_format = header_format
        self.cell_format = cell_format
        self._current_row = 0
        self._widths = len(self.columns) * [0]
        self.writerow_raw(self.columns)

    def writerow(self, values: dict):
        row = [values.get(col) for col in self.field_order]
        self.writerow_raw(row)

    def writerow_raw(self, cells: [Union[str, int]]):
        self.sheet.write_row(row=self._current_row, col=0, data=cells)
        self._current_row += 1
        for i, cell in enumerate(cells):
            self._widths[i] = max(self._widths[i], len(str(cell)))

    def finalize(self):
        for col, width in enumerate(self._widths):
            width = xslx_scale_column_width(width)
            self.sheet.set_column(col, col, width, self.cell_format)
        self.sheet.set_row(0, None, self.header_format)


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
