import csv
import os

import pytest
from logs.logic.export_analytical import CsvBackend


@pytest.mark.django_db
class TestAnalyticalExport:
    def test_csv(self, flexible_slicer_test_data):
        try:
            os.remove('/tmp/analytical_export_test.csv')
        except FileNotFoundError:
            pass

        CsvBackend(
            path='/tmp/analytical_export_test.csv',
            report_type=flexible_slicer_test_data['report_types'][1],
        ).export()

        with open('/tmp/analytical_export_test.csv', newline='') as fp:
            r = csv.reader(fp)
            header = (
                'id,metric_id,metric__short_name,organization_id,organization__name,platform_id,'
                'platform__name,title_id,title__name,title__pub_type,title__isbn,title__issn,'
                'title__eissn,title__doi,dim1name,dim2name,value,date,import_batch_id'.split(',')
            )
            assert r.__next__() == header
            count = {k: {} for k in (2, 4, 6, 8, 10, 14, 15)}
            for row in r:
                for k in count.keys():
                    count[k].setdefault(row[k], 0)
                    count[k][row[k]] += 1
            print(count)
            assert count == {
                2: {'m1': 1296, 'm2': 1296, 'm3': 1296},
                4: {'Organization 1': 1296, 'Organization 2': 1296, 'Organization 3': 1296},
                6: {'Platform 1': 1296, 'Platform 2': 1296, 'Platform 3': 1296},
                8: {'Title 1': 1296, 'Title 2': 1296, 'Title 3': 1296},
                10: {'123456789': 1296, '': 2592},
                14: {'A': 1296, 'B': 1296, 'C': 1296},
                15: {'XX': 972, 'YY': 972, 'ZZ': 972, 'A': 972},
            }
