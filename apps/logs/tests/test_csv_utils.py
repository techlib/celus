from io import StringIO

from ..logic.csv_utils import MappingDictWriter


class TestMappingDictWriter:
    def test_simple(self):
        out = StringIO()
        writer = MappingDictWriter(out, fields=[('a', 'A'), ('b', 'B')])
        writer.writerow({'a': 1, 'b': 2})
        assert out.getvalue().splitlines() == ['A,B', '1,2']
