import csv

import pyarrow.parquet as pq
import pytest
from core.fake_data import UserFactory
from tags.fake_data import TagClassFactory, TagFactory
from tags.models import AccessibleBy, OrganizationTag, PlatformTag, TitleTag

from logs.cubes import ch_backend
from logs.fake_data import DimensionTextFactory, ImportBatchFullFactory, ReportTypeFactory
from logs.logic.export_analytical import (
    CsvExport,
    HCubeExport,
    ParquetExport,
    convert_list_to_csv_row,
)
from logs.models import AccessLog, ImportBatch
from test_scenarios.basic import *  # noqa - fixtures


def other_tags(access_logs):
    tag_class = TagClassFactory.create(name="INTERNAL TAG CLASS", internal=True)
    tag1 = TagFactory.create(tag_class=tag_class, name="INTERNAL TAG")

    TitleTag.objects.create(tag=tag1, target_id=access_logs[0].target_id)


@pytest.fixture
def tag_data():
    tr = ReportTypeFactory()
    ib = ImportBatchFullFactory(report_type=tr)
    access_logs = list(AccessLog.objects.filter(import_batch=ib))

    tag_class = TagClassFactory.create(name="Test Tag Class", internal=False)
    tag1 = TagFactory.create(tag_class=tag_class, name="Tag1", can_see=AccessibleBy.EVERYBODY)
    tag2 = TagFactory.create(tag_class=tag_class, name="Tag2", can_see=AccessibleBy.EVERYBODY)
    tag3 = TagFactory.create(
        tag_class=tag_class, name="Tag3", can_see=AccessibleBy.OWNER, owner=UserFactory()
    )

    TitleTag.objects.create(tag=tag1, target_id=access_logs[0].target_id)
    TitleTag.objects.create(tag=tag1, target_id=access_logs[1].target_id)
    TitleTag.objects.create(tag=tag2, target_id=access_logs[1].target_id)
    TitleTag.objects.create(tag=tag3, target_id=access_logs[2].target_id)

    OrganizationTag.objects.create(tag=tag1, target_id=access_logs[0].organization_id)
    OrganizationTag.objects.create(tag=tag3, target_id=access_logs[0].organization_id)

    PlatformTag.objects.create(tag=tag1, target_id=access_logs[0].platform_id)
    PlatformTag.objects.create(tag=tag3, target_id=access_logs[0].platform_id)

    other_tags(access_logs)
    return locals()


def test_convert_list_to_csv_row():
    result = convert_list_to_csv_row(["Tag1", "Tag2"])
    assert result == "Tag1,Tag2"

    result = convert_list_to_csv_row(["Tag, with comma", 'Tag with "quotes"'])
    assert result == '"Tag, with comma","Tag with ""quotes"""'


@pytest.mark.clickhouse
@pytest.mark.usefixtures("clickhouse_on_off")
@pytest.mark.django_db(transaction=True)
class TestAnalyticalExport:
    # These represent the occurrences of a given value in a given
    # col. Only the columns mentioned are checked. It works but makes the test
    # unfortunately dependent on the test data.
    EXPECTED_DATA_SLICER = {
        "metric__short_name": {"m1": 1296, "m2": 1296, "m3": 1296},
        "organization__name": {
            "Organization 1": 1296,
            "Organization 2": 1296,
            "Organization 3": 1296,
        },
        "platform__name": {"Platform 1": 1296, "Platform 2": 1296, "Platform 3": 1296},
        "title__name": {"Title 1": 1296, "Title 2": 1296, "Title 3": 1296},
        "title__isbn": {"123456789": 1296, "": 2592},
        "dim1name": {"A": 1296, "B": 1296, "C": 1296},
        "dim2name": {"XX": 972, "YY": 972, "ZZ": 972, "A": 972},
    }

    def test_csv_slicer(self, flexible_slicer_test_data):
        path = "/tmp/analytical_export_test_slicer.csv"
        CsvExport(
            output=path,
            force_overwrite=True,
            report_type=flexible_slicer_test_data["report_types"][1],
        ).export()

        with open(path, newline="") as fp:
            reader = csv.DictReader(fp)
            header = (
                "metric_id,metric__short_name,organization_id,organization__name,platform_id,"
                "platform__name,title_id,title__name,title__pub_type,title__isbn,title__issn,"
                "title__eissn,title__doi,dim1name,dim2name,value,date,import_batch_id".split(",")
            )
            assert reader.fieldnames == header

            count = {k: {} for k in self.EXPECTED_DATA_SLICER.keys()}
            for row in reader:
                for k in count.keys():
                    count[k].setdefault(row[k], 0)
                    count[k][row[k]] += 1

            assert count == self.EXPECTED_DATA_SLICER

    def test_csv_factory(self):
        dt1 = DimensionTextFactory.create(text="translated1")
        dt2 = DimensionTextFactory.create(text="translated2")
        dimensions = [dt1.dimension.short_name, dt2.dimension.short_name]
        tr = ReportTypeFactory(dimensions=dimensions)
        ibs: list[ImportBatch] = [
            ImportBatchFullFactory(create_accesslogs__dim1=dt1.id),
            ImportBatchFullFactory(create_accesslogs__dim2=dt2.id),
            ImportBatchFullFactory(create_accesslogs__dim1=dt1.id, create_accesslogs__dim2=dt2.id),
            *ImportBatchFullFactory.create_batch(3, report_type=tr),
        ]

        path = "/tmp/analytical_export_test_factory.csv"
        backend = CsvExport(output=path, force_overwrite=True, report_type=tr)
        backend.export()
        with open(path, newline="") as fp:
            reader = csv.DictReader(fp)
            expected_header = list(backend.cols.values())
            assert dimensions[0] in expected_header
            assert dimensions[1] in expected_header
            assert reader.fieldnames == expected_header

            fields_reverse = {v: k for k, v in backend.cols.items()}

            # we're dealing with 100 rows from ImportBatches, so it's not slow
            count = 0
            for row in reader:
                count += 1
                assert (
                    AccessLog.objects.filter(
                        **{
                            fields_reverse[k]: (int(row[k]) if k.endswith("_id") else row[k])
                            for k in expected_header
                            if k not in dimensions
                        }
                    ).count()
                    == 1
                ), "row not found in db"

                # check for translations of DimensionText
                if int(row["import_batch_id"]) == ibs[0].id:
                    assert row[dimensions[0]] == "translated1"
                    assert row[dimensions[1]] == ""
                elif int(row["import_batch_id"]) == ibs[1].id:
                    assert row[dimensions[0]] == ""
                    assert row[dimensions[1]] == "translated2"
                elif int(row["import_batch_id"]) == ibs[2].id:
                    assert row[dimensions[0]] == "translated1"
                    assert row[dimensions[1]] == "translated2"
                else:
                    assert row[dimensions[0]] == ""
                    assert row[dimensions[1]] == ""
            assert count == AccessLog.objects.filter(report_type=tr).count()

    def test_export_with_tags(self, tag_data):
        tr = tag_data["tr"]
        access_logs = tag_data["access_logs"]

        path = "/tmp/analytical_export_test_tags.csv"
        backend = CsvExport(output=path, force_overwrite=True, report_type=tr, tags=True)
        backend.export()

        with open(path, newline="") as fp:
            reader = csv.DictReader(fp)
            assert "tags" in reader.fieldnames
            assert "internal_tags" in reader.fieldnames
            assert "platform_tags" in reader.fieldnames
            assert "organization_tags" in reader.fieldnames

            for row in reader:
                if row["title_id"] == str(access_logs[0].target_id):
                    assert row["tags"] == "Test Tag Class / Tag1"
                    assert row["internal_tags"] == "INTERNAL TAG CLASS / INTERNAL TAG"
                    assert row["platform_tags"] == "Test Tag Class / Tag1"
                    assert row["organization_tags"] == "Test Tag Class / Tag1"
                elif row["title_id"] == str(access_logs[1].target_id):
                    assert row["tags"] == "Test Tag Class / Tag1,Test Tag Class / Tag2"
                else:
                    assert row["tags"] == ""

    def test_parquet_slicer(self, flexible_slicer_test_data):
        path = "/tmp/analytical_export_test_slicer.parquet"
        ParquetExport(
            output=path,
            force_overwrite=True,
            report_type=flexible_slicer_test_data["report_types"][1],
        ).export()

        table = pq.read_table(path)
        expected_columns = (
            "metric_id,metric__short_name,organization_id,organization__name,platform_id,"
            "platform__name,title_id,title__name,title__pub_type,title__isbn,title__issn,"
            "title__eissn,title__doi,dim1name,dim2name,value,date,import_batch_id".split(",")
        )
        assert list(table.column_names) == expected_columns

        # Check that we have the expected data
        assert table.num_rows > 0
        metric_names = table.column("metric__short_name").to_pylist()
        org_names = table.column("organization__name").to_pylist()
        platform_names = table.column("platform__name").to_pylist()
        assert "m1" in metric_names
        assert "Organization 1" in org_names
        assert "Platform 1" in platform_names

        # Check data types
        metric_ids = table.column("metric_id").to_pylist()
        title_ids = table.column("title_id").to_pylist()
        values = table.column("value").to_pylist()
        assert all(isinstance(x, int) for x in metric_ids), (
            f"Expected integers for metric_id, got {[type(x) for x in metric_ids[:3]]}"
        )
        assert all(isinstance(x, int) for x in title_ids), (
            f"Expected integers for title_id, got {[type(x) for x in title_ids[:3]]}"
        )
        assert all(isinstance(x, int) for x in values), (
            f"Expected integers for value, got {[type(x) for x in values[:3]]}"
        )

    def test_parquet_with_tags(self, tag_data):
        tr = tag_data["tr"]
        access_logs = tag_data["access_logs"]

        path = "/tmp/analytical_export_test_tags.parquet"
        backend = ParquetExport(output=path, force_overwrite=True, report_type=tr, tags=True)
        backend.export()

        table = pq.read_table(path)
        assert "tags" in table.column_names

        # Check tags for specific titles
        title_ids = table.column("title_id").to_pylist()
        tags = table.column("tags").to_pylist()

        for i, title_id in enumerate(title_ids):
            if title_id == access_logs[0].target_id:
                assert tags[i] == ["Test Tag Class / Tag1"]
            elif title_id == access_logs[1].target_id:
                assert tags[i] == ["Test Tag Class / Tag1", "Test Tag Class / Tag2"]
            else:
                assert tags[i] == []


@pytest.mark.clickhouse
@pytest.mark.usefixtures("clickhouse_db")
@pytest.mark.django_db(transaction=True)
class TestHCubeExport:
    def test_hcube_clickhouse(self, flexible_slicer_test_data):
        table = "test_hcube_export_clickhouse"
        rt = flexible_slicer_test_data["report_types"][1]

        export = HCubeExport(cube_backend=ch_backend, table=table, report_type=rt)
        export.cube_backend.drop_storage(export.cube)
        export.cube_backend.initialize_storage(export.cube)
        export.export()

        count = {k: {} for k in TestAnalyticalExport.EXPECTED_DATA_SLICER.keys()}
        for row in export.cube_backend.get_records(export.cube.query()):
            for k in count.keys():
                val = getattr(row, k)
                count[k].setdefault(val, 0)
                count[k][val] += 1

        assert count == TestAnalyticalExport.EXPECTED_DATA_SLICER
        with export.cube_backend.pool.get_client() as client:
            comment = client.execute(
                "SELECT comment FROM system.tables WHERE database = %(db)s AND name = %(table)s;",
                {"db": export.cube_backend.database, "table": table},
            )[0][0]
            assert "last update: " in comment, "Expected the comment to be set on the table"
            assert rt.name in comment, "Expected the report type name to be in the comment"

        export = HCubeExport(cube_backend=ch_backend, table=table, report_type=rt)
        assert export.export() == 0, "exporting twice shouldn't update anything"

        export.cube_backend.drop_storage(export.cube)

    def test_hcube_clickhouse_tags(self, tag_data):
        tr = tag_data["tr"]
        access_logs = tag_data["access_logs"]

        table = "test_hcube_export_clickhouse"
        export = HCubeExport(cube_backend=ch_backend, table=table, report_type=tr, tags=True)
        export.cube_backend.drop_storage(export.cube)
        export.cube_backend.initialize_storage(export.cube)
        export.export()

        for row in export.cube_backend.get_records(export.cube.query()):
            if row.title_id == access_logs[0].target_id:
                assert row.tags == ["Test Tag Class / Tag1"]
            elif row.title_id == access_logs[1].target_id:
                assert row.tags == ["Test Tag Class / Tag1", "Test Tag Class / Tag2"]
            else:
                assert row.tags == []

        export.cube_backend.drop_storage(export.cube)
