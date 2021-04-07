from csv import writer
from typing import Tuple, List


class MappingDictWriter:
    """
    Special DictWriter that maps column names from row keys to different column names
    """

    def __init__(self, stream, fields: List[Tuple[str, str]], *args, **kwargs):
        self.stream = stream
        self.writer = writer(stream, *args, **kwargs)
        self.field_order = []
        self.columns = []
        for key, column in fields:
            self.field_order.append(key)
            self.columns.append(column)
        self.writer.writerow(self.columns)

    def writerow(self, values: dict):
        row = [values.get(col) for col in self.field_order]
        self.writer.writerow(row)
