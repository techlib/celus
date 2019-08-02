import json

import pytest

from ..counter5 import Counter5ReportBase, CounterRecord, Counter5TRReport


class TestCounter5Reading(object):

    data_simple = '''
      {
      "Report_Items": [
        {
          "Title": "Title1",
          "Publisher": "Pub1",
          "Item_ID": [
            {
              "Type": "ISBN",
              "Value": "978-1-111111-01-1"
            }
          ],
          "Section_Type": "Chapter",
          "Platform": "PlOne",
          "Data_Type": "Book",
          "YOP": "2009",
          "Access_Type": "OA_Gold",
          "Access_Method": "Regular",
          "Performance": [
            {
              "Period": {
                "Begin_Date": "2019-05-01",
                "End_Date": "2019-05-31"
              },
              "Instance": [
                {
                  "Metric_Type": "Total_Item_Investigations",
                  "Count": 10
                },
                {
                  "Metric_Type": "Total_Item_Requests",
                  "Count": 8
                }
              ]
            }
          ]
        }
      ]
      }
    '''

    def test_record_simple(self):
        data = json.loads(self.data_simple)
        reader = Counter5ReportBase()
        records = reader.read_report(data)
        assert len(records) == 2
        assert records[0].platform_name == 'PlOne'
        assert records[0].title == 'Title1'
        assert records[0].metric == 'Total_Item_Investigations'
        assert records[0].value == 10
        assert records[0].start == '2019-05-01'
        assert records[0].end == '2019-05-31'
        assert records[0].dimension_data == {}
        assert records[1].value == 8
        # both records should have the same values for these attributes as they come from the
        # same item in the data
        for attr in ('platform_name', 'title', 'start', 'end'):
            assert getattr(records[0], attr) == getattr(records[1], attr)

    def test_record_simple_tr(self):
        data = json.loads(self.data_simple)
        reader = Counter5TRReport()
        records = reader.read_report(data)
        assert len(records) == 2
        assert records[0].value == 10
        # just test what is different in TR report
        assert records[0].dimension_data == {
            'Access_Type': 'OA_Gold',
            'Publisher': 'Pub1',
            'Access_Method': 'Regular',
            'YOP': '2009',
            'Section_Type': 'Chapter',
            'Data_Type': 'Book',
        }
