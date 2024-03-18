import typing

import pytest
from logs.fake_data import (
    AccessLogFactory,
    DimensionFactory,
    DimensionTextFactory,
    ImportBatchFactory,
    MetricFactory,
    ReportTypeFactory,
)
from logs.models import DimensionText, ReportType
from publications.fake_data import AuthorFactory, ItemFactory, TitleFactory
from sushi.fake_data import CounterReportTypeFactory


def map_dimensions(
    report_type: ReportType,
    dim_text_map: typing.Dict[str, typing.Dict[str, DimensionText]],
    assignment: typing.Dict[str, str],
) -> typing.Dict[str, int]:
    return {
        report_type.dim_name_to_dim_attr(k): dim_text_map[k][v].pk for k, v in assignment.items()
    }


@pytest.fixture
def counter_report_types(tr, dr, pr, ir_m1, ir):
    tr = CounterReportTypeFactory(counter_version=5, code=tr.short_name, report_type=tr)
    dr = CounterReportTypeFactory(counter_version=5, code=dr.short_name, report_type=dr)
    pr = CounterReportTypeFactory(counter_version=5, code=pr.short_name, report_type=pr)
    ir_m1 = CounterReportTypeFactory(counter_version=5, code=ir_m1.short_name, report_type=ir_m1)
    ir = CounterReportTypeFactory(counter_version=5, code=ir.short_name, report_type=ir)
    return locals()


@pytest.fixture
def targets():
    target1 = TitleFactory(
        name="target1",
        doi="10.4324/9781003185581",
        isbn="9781003185581",
        issn="1111-1111",
        eissn="9111-1111",
    )
    target2 = TitleFactory(name="target2", isbn="9781492084884", issn="", eissn="", doi="")
    target3 = TitleFactory(name="target3", isbn="", issn="", eissn="", doi="")
    return locals()


@pytest.fixture
def items():
    item11 = ItemFactory(
        name="J11", doi="10.1111/1111.1111.1111", isbn="", issn="1111-1111", eissn="9111-1111"
    )
    item12 = ItemFactory(
        name="J12", doi="10.1111/1111.1111.2222", isbn="", issn="1111-1111", eissn="9111-1111"
    )
    item21 = ItemFactory(name="J21", doi="10.2222/1111.2222.1111", isbn="", issn="", eissn="")
    item31 = ItemFactory(
        name="M31",
        doi="",
        isbn="",
        issn="",
        eissn="",
        publication_date="2021-12-24",
        uris=["https://example.org/song"],
        authors=[
            AuthorFactory(name="MM", orcid="1234123412341234", isni=""),
            AuthorFactory(name="MM, M", isni="", orcid=""),
        ],
    )
    return locals()


@pytest.fixture
def metrics():
    searches_regular = MetricFactory(short_name="Searches_Regular")
    searches_automated = MetricFactory(short_name="Searches_Automated")
    searches_federated = MetricFactory(short_name="Searches_Federated")
    searches_platform = MetricFactory(short_name="Searches_Platform")

    total_item_investigations = MetricFactory(short_name="Total_Item_Investigations ")
    unique_item_investigations = MetricFactory(short_name="Unique_Item_Investigations")
    unique_title_investigations = MetricFactory(short_name="Unique_Title_Investigations")
    total_item_requests = MetricFactory(short_name="Total_Item_Requests")
    unique_item_requests = MetricFactory(short_name="Unique_Item_Requests")
    unique_title_requests = MetricFactory(short_name="Unique_Title_Requests")

    no_license = MetricFactory(short_name="No_License")
    limit_exceeded = MetricFactory(short_name="Limit_Exceeded")

    return locals()


@pytest.fixture
def dimensions():
    Access_Type = DimensionFactory(short_name="Access_Type")
    Access_Method = DimensionFactory(short_name="Access_Method")
    Data_Type = DimensionFactory(short_name="Data_Type")
    Parent_Data_Type = DimensionFactory(short_name="Parent_Data_Type")
    Section_Type = DimensionFactory(short_name="Section_Type")
    YOP = DimensionFactory(short_name="YOP")
    Publisher = DimensionFactory(short_name="Publisher")
    Platform = DimensionFactory(short_name="Platform")
    Article_Version = DimensionFactory(short_name="Article_Version")

    return locals()


@pytest.fixture
def dimension_texts(dimensions):
    texts = {
        "Access_Type": {
            "Controlled": DimensionTextFactory(
                dimension=dimensions["Access_Type"], text="Controlled"
            ),
            "OA_Gold": DimensionTextFactory(dimension=dimensions["Access_Type"], text="OA_Gold"),
            "OA_Delayed": DimensionTextFactory(
                dimension=dimensions["Access_Type"], text="OA_Delayed"
            ),
            "Other_Free_To_Read": DimensionTextFactory(
                dimension=dimensions["Access_Type"], text="Other_Free_To_Read"
            ),
        },
        "Access_Method": {
            "Regular": DimensionTextFactory(dimension=dimensions["Access_Method"], text="Regular"),
            "TDM": DimensionTextFactory(dimension=dimensions["Access_Method"], text="TDM"),
        },
        "Data_Type": {
            "Article": DimensionTextFactory(dimension=dimensions["Data_Type"], text="Article"),
            "Book": DimensionTextFactory(dimension=dimensions["Data_Type"], text="Book"),
            "Book_Segment": DimensionTextFactory(
                dimension=dimensions["Data_Type"], text="Book_Segment"
            ),
            "Database": DimensionTextFactory(dimension=dimensions["Data_Type"], text="Database"),
            "Dataset": DimensionTextFactory(dimension=dimensions["Data_Type"], text="Dataset"),
            "Journal": DimensionTextFactory(dimension=dimensions["Data_Type"], text="Journal"),
            "Multimedia": DimensionTextFactory(
                dimension=dimensions["Data_Type"], text="Multimedia"
            ),
            "Newspaper_or_Newsletter": DimensionTextFactory(
                dimension=dimensions["Data_Type"], text="Newspaper_or_Newsletter"
            ),
            "Other": DimensionTextFactory(dimension=dimensions["Data_Type"], text="Other"),
            "Platform": DimensionTextFactory(dimension=dimensions["Data_Type"], text="Platform"),
            "Report": DimensionTextFactory(dimension=dimensions["Data_Type"], text="Report"),
            "Repository_Item": DimensionTextFactory(
                dimension=dimensions["Data_Type"], text="Repository_Item"
            ),
            "Thesis_or_Dissertation": DimensionTextFactory(
                dimension=dimensions["Data_Type"], text="Thesis_or_Dissertation"
            ),
            "Unspecified": DimensionTextFactory(
                dimension=dimensions["Data_Type"], text="Unspecified"
            ),
        },
        "Section_Type": {
            "Article": DimensionTextFactory(dimension=dimensions["Section_Type"], text="Article"),
            "Book": DimensionTextFactory(dimension=dimensions["Section_Type"], text="Book"),
            "Chapter": DimensionTextFactory(dimension=dimensions["Section_Type"], text="Chapter"),
            "Other": DimensionTextFactory(dimension=dimensions["Section_Type"], text="Other"),
            "Section": DimensionTextFactory(dimension=dimensions["Section_Type"], text="Section"),
        },
        "YOP": {
            "0001": DimensionTextFactory(dimension=dimensions["YOP"], text="0001"),
            "2020": DimensionTextFactory(dimension=dimensions["YOP"], text="2020"),
            "2021": DimensionTextFactory(dimension=dimensions["YOP"], text="2021"),
            "2022": DimensionTextFactory(dimension=dimensions["YOP"], text="2022"),
            "2023": DimensionTextFactory(dimension=dimensions["YOP"], text="2023"),
            "9999": DimensionTextFactory(dimension=dimensions["YOP"], text="9999"),
        },
        "Publisher": {
            "Pub1": DimensionTextFactory(dimension=dimensions["Publisher"], text="Pub1"),
            "Pub2": DimensionTextFactory(dimension=dimensions["Publisher"], text="Pub2"),
            "Pub3": DimensionTextFactory(dimension=dimensions["Publisher"], text="Pub3"),
        },
        "Platform": {
            "Plat1": DimensionTextFactory(dimension=dimensions["Platform"], text="Plat1"),
            "Plat2": DimensionTextFactory(dimension=dimensions["Platform"], text="Plat2"),
            "Plat3": DimensionTextFactory(dimension=dimensions["Platform"], text="Plat3"),
        },
        "Article_Version": {
            "AM": DimensionTextFactory(dimension=dimensions["Article_Version"], text="AM"),
            "VoR": DimensionTextFactory(dimension=dimensions["Article_Version"], text="VoR"),
            "CVoR": DimensionTextFactory(dimension=dimensions["Article_Version"], text="CVoR"),
            "EVoR": DimensionTextFactory(dimension=dimensions["Article_Version"], text="EVoR"),
        },
    }

    texts["Parent_Data_Type"] = texts["Data_Type"]

    return texts


@pytest.fixture
def tr(dimensions):
    return ReportTypeFactory(
        name="Counter 5 - Title Report",
        short_name="TR",
        dimensions=[
            dimensions["Access_Type"],
            dimensions["Access_Method"],
            dimensions["Data_Type"],
            dimensions["Section_Type"],
            dimensions["YOP"],
            dimensions["Publisher"],
            dimensions["Platform"],
        ],
    )


@pytest.fixture
def dr(dimensions):
    return ReportTypeFactory(
        name="Counter 5 - Database Report",
        short_name="DR",
        dimensions=[
            dimensions["Access_Method"],
            dimensions["Data_Type"],
            dimensions["Publisher"],
            dimensions["Platform"],
        ],
    )


@pytest.fixture
def pr(dimensions):
    return ReportTypeFactory(
        name="Counter 5 - Platform Report",
        short_name="PR",
        dimensions=[dimensions["Access_Method"], dimensions["Data_Type"], dimensions["Platform"]],
    )


@pytest.fixture
def ir_m1(dimensions):
    return ReportTypeFactory(
        name="Counter 5 - Multimedia Item Report 1",
        short_name="IR_M1",
        dimensions=[dimensions["Publisher"], dimensions["Platform"]],
    )


@pytest.fixture
def ir(dimensions):
    return ReportTypeFactory(
        name="Counter 5 - Item Report",
        short_name="IR",
        dimensions=[
            dimensions["Publisher"],
            dimensions["Platform"],
            dimensions["Access_Type"],
            dimensions["Access_Method"],
            dimensions["Data_Type"],
            dimensions["Parent_Data_Type"],
            dimensions["YOP"],
            dimensions["Article_Version"],
        ],
    )


@pytest.fixture
def tr_dim(tr, dimension_texts):
    def mapper(**kwargs: typing.Dict[str, str]) -> typing.Dict[str, int]:
        return map_dimensions(tr, dimension_texts, kwargs)

    return mapper


@pytest.fixture
def dr_dim(dr, dimension_texts):
    def mapper(**kwargs: typing.Dict[str, str]) -> typing.Dict[str, int]:
        return map_dimensions(dr, dimension_texts, kwargs)

    return mapper


@pytest.fixture
def pr_dim(pr, dimension_texts):
    def mapper(**kwargs: typing.Dict[str, str]) -> typing.Dict[str, int]:
        return map_dimensions(pr, dimension_texts, kwargs)

    return mapper


@pytest.fixture
def ir_dim(ir, dimension_texts):
    def mapper(**kwargs: typing.Dict[str, str]) -> typing.Dict[str, int]:
        return map_dimensions(ir, dimension_texts, kwargs)

    return mapper


@pytest.fixture
def ir_m1_dim(ir_m1, dimension_texts):
    def mapper(**kwargs: typing.Dict[str, str]) -> typing.Dict[str, int]:
        return map_dimensions(ir_m1, dimension_texts, kwargs)

    return mapper


@pytest.fixture
def tr_ibs(organization, tr, tr_dim, platform, targets, metrics):
    ib1 = ImportBatchFactory(
        date="2020-02-01", organization=organization, platform=platform, report_type=tr
    )
    ib2 = ImportBatchFactory(
        date="2020-04-01", organization=organization, platform=platform, report_type=tr
    )
    ib3 = ImportBatchFactory(
        date="2019-12-01", organization=organization, platform=platform, report_type=tr
    )
    ib4 = ImportBatchFactory(
        date="2021-01-01", organization=organization, platform=platform, report_type=tr
    )
    AccessLogFactory(
        import_batch=ib1,
        value=1,
        target=targets["target1"],
        **tr_dim(
            Access_Type="Controlled",
            Access_Method="Regular",
            Data_Type="Book",
            Section_Type="Book",
            YOP="2020",
            Publisher="Pub1",
            Platform="Plat1",
        ),
        metric=metrics["total_item_requests"],
    )
    AccessLogFactory(
        import_batch=ib1,
        value=3,
        target=targets["target1"],
        **tr_dim(
            Access_Type="Controlled",
            Access_Method="Regular",
            Data_Type="Book",
            Section_Type="Book",
            YOP="2020",
            Publisher="Pub1",
            Platform="Plat1",
        ),
        metric=metrics["no_license"],
    )
    AccessLogFactory(
        import_batch=ib1,
        value=23,
        target=targets["target2"],
        **tr_dim(
            Access_Type="Controlled",
            Access_Method="Regular",
            Data_Type="Journal",
            Section_Type="Article",
            YOP="2022",
            Publisher="Pub1",
            Platform="Plat1",
        ),
        metric=metrics["total_item_requests"],
    )
    AccessLogFactory(
        import_batch=ib1,
        value=29,
        target=targets["target2"],
        **tr_dim(
            Access_Type="Controlled",
            Access_Method="Regular",
            Data_Type="Journal",
            Section_Type="Article",
            YOP="2022",
            Publisher="Pub1",
            Platform="Plat1",
        ),
        metric=metrics["no_license"],
    )
    AccessLogFactory(
        import_batch=ib2,
        value=5,
        target=targets["target1"],
        **tr_dim(
            Access_Type="Controlled",
            Access_Method="Regular",
            Data_Type="Book",
            Section_Type="Book",
            YOP="2020",
            Publisher="Pub1",
            Platform="Plat1",
        ),
        metric=metrics["total_item_requests"],
    )
    AccessLogFactory(
        import_batch=ib2,
        value=7,
        target=targets["target1"],
        **tr_dim(
            Access_Type="Controlled",
            Access_Method="Regular",
            Data_Type="Book",
            Section_Type="Book",
            YOP="2020",
            Publisher="Pub1",
            Platform="Plat1",
        ),
        metric=metrics["no_license"],
    )
    AccessLogFactory(
        import_batch=ib2,
        value=31,
        target=targets["target3"],
        **tr_dim(
            Access_Type="Controlled",
            Access_Method="Regular",
            Data_Type="Other",
            Section_Type="Chapter",
            YOP="2021",
            Publisher="Pub1",
            Platform="Plat1",
        ),
        metric=metrics["total_item_requests"],
    )
    AccessLogFactory(
        import_batch=ib2,
        value=37,
        target=targets["target3"],
        **tr_dim(
            Access_Type="Controlled",
            Access_Method="Regular",
            Data_Type="Other",
            Section_Type="Chapter",
            YOP="2021",
            Publisher="Pub1",
            Platform="Plat1",
        ),
        metric=metrics["no_license"],
    )

    # before
    AccessLogFactory(
        import_batch=ib3,
        value=11,
        target=targets["target1"],
        **tr_dim(
            Access_Type="Controlled",
            Access_Method="Regular",
            Data_Type="Book",
            Section_Type="Book",
            YOP="2020",
            Publisher="Pub1",
            Platform="Plat1",
        ),
        metric=metrics["total_item_requests"],
    )
    AccessLogFactory(
        import_batch=ib3,
        value=13,
        target=targets["target1"],
        **tr_dim(
            Access_Type="Controlled",
            Access_Method="Regular",
            Data_Type="Book",
            Section_Type="Book",
            YOP="2020",
            Publisher="Pub1",
            Platform="Plat1",
        ),
        metric=metrics["no_license"],
    )

    # after
    AccessLogFactory(
        import_batch=ib4,
        value=17,
        target=targets["target1"],
        **tr_dim(
            Access_Type="Controlled",
            Access_Method="Regular",
            Data_Type="Book",
            Section_Type="Book",
            YOP="2020",
            Publisher="Pub1",
            Platform="Plat1",
        ),
        metric=metrics["no_license"],
    )
    AccessLogFactory(
        import_batch=ib4,
        value=19,
        target=targets["target1"],
        **tr_dim(
            Access_Type="Controlled",
            Access_Method="Regular",
            Data_Type="Book",
            Section_Type="Book",
            YOP="2020",
            Publisher="Pub1",
            Platform="Plat1",
        ),
        metric=metrics["total_item_requests"],
    )

    return ib1, ib2, ib3, ib4


@pytest.fixture
def dr_ibs(organization, dr, dr_dim, platform, targets, metrics):
    ib1 = ImportBatchFactory(
        date="2020-02-01", organization=organization, platform=platform, report_type=dr
    )
    ib2 = ImportBatchFactory(
        date="2020-04-01", organization=organization, platform=platform, report_type=dr
    )
    ib3 = ImportBatchFactory(
        date="2019-12-01", organization=organization, platform=platform, report_type=dr
    )
    ib4 = ImportBatchFactory(
        date="2021-01-01", organization=organization, platform=platform, report_type=dr
    )
    AccessLogFactory(
        import_batch=ib1,
        value=1,
        target=targets["target2"],
        **dr_dim(Access_Method="Regular", Data_Type="Book", Publisher="Pub1", Platform="Plat1"),
        metric=metrics["total_item_requests"],
    )
    AccessLogFactory(
        import_batch=ib1,
        value=3,
        target=targets["target2"],
        **dr_dim(Access_Method="Regular", Data_Type="Book", Publisher="Pub1", Platform="Plat1"),
        metric=metrics["no_license"],
    )
    AccessLogFactory(
        import_batch=ib1,
        value=23,
        target=targets["target1"],
        **dr_dim(Access_Method="Regular", Data_Type="Journal", Publisher="Pub1", Platform="Plat1"),
        metric=metrics["total_item_requests"],
    )
    AccessLogFactory(
        import_batch=ib1,
        value=29,
        target=targets["target1"],
        **dr_dim(Access_Method="Regular", Data_Type="Journal", Publisher="Pub1", Platform="Plat1"),
        metric=metrics["no_license"],
    )
    AccessLogFactory(
        import_batch=ib2,
        value=5,
        target=targets["target2"],
        **dr_dim(Access_Method="Regular", Data_Type="Book", Publisher="Pub1", Platform="Plat1"),
        metric=metrics["total_item_requests"],
    )
    AccessLogFactory(
        import_batch=ib2,
        value=7,
        target=targets["target2"],
        **dr_dim(Access_Method="Regular", Data_Type="Book", Publisher="Pub1", Platform="Plat1"),
        metric=metrics["no_license"],
    )
    AccessLogFactory(
        import_batch=ib2,
        value=31,
        target=targets["target3"],
        **dr_dim(Access_Method="Regular", Data_Type="Other", Publisher="Pub1", Platform="Plat1"),
        metric=metrics["total_item_requests"],
    )
    AccessLogFactory(
        import_batch=ib2,
        value=37,
        target=targets["target3"],
        **dr_dim(Access_Method="Regular", Data_Type="Other", Publisher="Pub1", Platform="Plat1"),
        metric=metrics["no_license"],
    )

    # before
    AccessLogFactory(
        import_batch=ib3,
        value=11,
        target=targets["target2"],
        **dr_dim(Access_Method="Regular", Data_Type="Book", Publisher="Pub1", Platform="Plat1"),
        metric=metrics["total_item_requests"],
    )
    AccessLogFactory(
        import_batch=ib3,
        value=13,
        target=targets["target2"],
        **dr_dim(Access_Method="Regular", Data_Type="Book", Publisher="Pub1", Platform="Plat1"),
        metric=metrics["no_license"],
    )

    # after
    AccessLogFactory(
        import_batch=ib4,
        value=17,
        target=targets["target2"],
        **dr_dim(Access_Method="Regular", Data_Type="Book", Publisher="Pub1", Platform="Plat1"),
        metric=metrics["no_license"],
    )
    AccessLogFactory(
        import_batch=ib4,
        date="2021-01-01",
        value=19,
        target=targets["target2"],
        **dr_dim(Access_Method="Regular", Data_Type="Book", Publisher="Pub1", Platform="Plat1"),
        metric=metrics["total_item_requests"],
    )

    return ib1, ib2, ib3, ib4


@pytest.fixture
def pr_ibs(organization, pr, pr_dim, platform, targets, metrics):
    ib1 = ImportBatchFactory(
        date="2020-02-01", organization=organization, platform=platform, report_type=pr
    )
    ib2 = ImportBatchFactory(
        date="2020-04-01", organization=organization, platform=platform, report_type=pr
    )
    ib3 = ImportBatchFactory(
        date="2019-12-01", organization=organization, platform=platform, report_type=pr
    )
    ib4 = ImportBatchFactory(
        date="2021-01-01", organization=organization, platform=platform, report_type=pr
    )
    AccessLogFactory(
        import_batch=ib1,
        value=1,
        target=targets["target3"],
        **pr_dim(Access_Method="Regular", Data_Type="Book", Platform="Plat1"),
        metric=metrics["total_item_requests"],
    )
    AccessLogFactory(
        import_batch=ib1,
        value=3,
        target=targets["target3"],
        **pr_dim(Access_Method="Regular", Data_Type="Book", Platform="Plat1"),
        metric=metrics["no_license"],
    )
    AccessLogFactory(
        import_batch=ib1,
        value=23,
        target=targets["target3"],
        **pr_dim(Access_Method="Regular", Data_Type="Journal", Platform="Plat1"),
        metric=metrics["total_item_requests"],
    )
    AccessLogFactory(
        import_batch=ib1,
        value=29,
        target=targets["target3"],
        **pr_dim(Access_Method="Regular", Data_Type="Journal", Platform="Plat1"),
        metric=metrics["no_license"],
    )
    AccessLogFactory(
        import_batch=ib2,
        value=5,
        target=targets["target3"],
        **pr_dim(Access_Method="Regular", Data_Type="Book", Platform="Plat1"),
        metric=metrics["total_item_requests"],
    )
    AccessLogFactory(
        import_batch=ib2,
        value=7,
        target=targets["target3"],
        **pr_dim(Access_Method="Regular", Data_Type="Book", Platform="Plat1"),
        metric=metrics["no_license"],
    )
    AccessLogFactory(
        import_batch=ib2,
        value=31,
        target=targets["target1"],
        **pr_dim(Access_Method="Regular", Data_Type="Other", Platform="Plat1"),
        metric=metrics["total_item_requests"],
    )
    AccessLogFactory(
        import_batch=ib2,
        value=37,
        target=targets["target1"],
        **pr_dim(Access_Method="Regular", Data_Type="Other", Platform="Plat1"),
        metric=metrics["no_license"],
    )

    # before
    AccessLogFactory(
        import_batch=ib3,
        value=11,
        target=targets["target3"],
        **pr_dim(Access_Method="Regular", Data_Type="Book", Platform="Plat1"),
        metric=metrics["total_item_requests"],
    )
    AccessLogFactory(
        import_batch=ib3,
        value=13,
        target=targets["target3"],
        **pr_dim(Access_Method="Regular", Data_Type="Book", Platform="Plat1"),
        metric=metrics["no_license"],
    )

    # after
    AccessLogFactory(
        import_batch=ib4,
        value=17,
        target=targets["target3"],
        **pr_dim(Access_Method="Regular", Data_Type="Book", Platform="Plat1"),
        metric=metrics["no_license"],
    )
    AccessLogFactory(
        import_batch=ib4,
        value=19,
        target=targets["target3"],
        **pr_dim(Access_Method="Regular", Data_Type="Book", Platform="Plat1"),
        metric=metrics["total_item_requests"],
    )

    return ib1, ib2, ib3, ib4


@pytest.fixture
def ir_m1_ibs(organization, ir_m1, ir_m1_dim, platform, targets, metrics):
    ib1 = ImportBatchFactory(
        date="2020-02-01", organization=organization, platform=platform, report_type=ir_m1
    )
    ib2 = ImportBatchFactory(
        date="2020-04-01", organization=organization, platform=platform, report_type=ir_m1
    )
    ib3 = ImportBatchFactory(
        date="2019-12-01", organization=organization, platform=platform, report_type=ir_m1
    )
    ib4 = ImportBatchFactory(
        date="2021-01-01", organization=organization, platform=platform, report_type=ir_m1
    )
    AccessLogFactory(
        import_batch=ib1,
        date="2020-02-01",
        value=1,
        target=targets["target1"],
        **ir_m1_dim(Publisher="Pub1", Platform="Plat1"),
        metric=metrics["total_item_requests"],
    )
    AccessLogFactory(
        import_batch=ib1,
        date="2020-02-01",
        value=3,
        target=targets["target1"],
        **ir_m1_dim(Publisher="Pub1", Platform="Plat1"),
        metric=metrics["no_license"],
    )
    AccessLogFactory(
        import_batch=ib1,
        date="2020-02-01",
        value=23,
        target=targets["target2"],
        **ir_m1_dim(Publisher="Pub1", Platform="Plat1"),
        metric=metrics["total_item_requests"],
    )
    AccessLogFactory(
        import_batch=ib1,
        date="2020-02-01",
        value=29,
        target=targets["target2"],
        **ir_m1_dim(Publisher="Pub1", Platform="Plat1"),
        metric=metrics["no_license"],
    )
    AccessLogFactory(
        import_batch=ib2,
        date="2020-04-01",
        value=5,
        target=targets["target1"],
        **ir_m1_dim(Publisher="Pub1", Platform="Plat1"),
        metric=metrics["total_item_requests"],
    )
    AccessLogFactory(
        import_batch=ib2,
        date="2020-04-01",
        value=7,
        target=targets["target1"],
        **ir_m1_dim(Publisher="Pub1", Platform="Plat1"),
        metric=metrics["no_license"],
    )
    AccessLogFactory(
        import_batch=ib2,
        date="2020-04-01",
        value=31,
        target=targets["target3"],
        **ir_m1_dim(Publisher="Pub1", Platform="Plat1"),
        metric=metrics["total_item_requests"],
    )
    AccessLogFactory(
        import_batch=ib2,
        date="2020-04-01",
        value=37,
        target=targets["target3"],
        **ir_m1_dim(Publisher="Pub1", Platform="Plat1"),
        metric=metrics["no_license"],
    )

    # before
    AccessLogFactory(
        import_batch=ib3,
        date="2019-12-01",
        value=11,
        target=targets["target1"],
        **ir_m1_dim(Publisher="Pub1", Platform="Plat1"),
        metric=metrics["total_item_requests"],
    )
    AccessLogFactory(
        import_batch=ib3,
        date="2019-12-01",
        value=13,
        target=targets["target1"],
        **ir_m1_dim(Publisher="Pub1", Platform="Plat1"),
        metric=metrics["no_license"],
    )

    # after
    AccessLogFactory(
        import_batch=ib4,
        date="2021-01-01",
        value=17,
        target=targets["target1"],
        **ir_m1_dim(Publisher="Pub1", Platform="Plat1"),
        metric=metrics["no_license"],
    )
    AccessLogFactory(
        import_batch=ib4,
        date="2021-01-01",
        value=19,
        target=targets["target1"],
        **ir_m1_dim(Publisher="Pub1", Platform="Plat1"),
        metric=metrics["total_item_requests"],
    )

    return ib1, ib2, ib3, ib4


@pytest.fixture
def ir_ibs(organization, ir, ir_dim, platform, targets, items, metrics):
    ib1 = ImportBatchFactory(
        date="2020-02-01", organization=organization, platform=platform, report_type=ir
    )
    ib2 = ImportBatchFactory(
        date="2020-04-01", organization=organization, platform=platform, report_type=ir
    )
    ib3 = ImportBatchFactory(
        date="2019-12-01", organization=organization, platform=platform, report_type=ir
    )
    ib4 = ImportBatchFactory(
        date="2021-01-01", organization=organization, platform=platform, report_type=ir
    )
    AccessLogFactory(
        import_batch=ib1,
        date="2020-02-01",
        value=1,
        target=targets["target1"],
        item=items["item11"],
        **ir_dim(Publisher="Pub1", Platform="Plat1"),
        metric=metrics["total_item_requests"],
    )
    AccessLogFactory(
        import_batch=ib1,
        date="2020-02-01",
        value=3,
        target=targets["target1"],
        item=items["item12"],
        **ir_dim(Publisher="Pub1", Platform="Plat1"),
        metric=metrics["no_license"],
    )
    AccessLogFactory(
        import_batch=ib1,
        date="2020-02-01",
        value=23,
        target=targets["target2"],
        item=items["item21"],
        **ir_dim(Publisher="Pub1", Platform="Plat1"),
        metric=metrics["total_item_requests"],
    )
    AccessLogFactory(
        import_batch=ib1,
        date="2020-02-01",
        value=29,
        target=targets["target2"],
        item=items["item21"],
        **ir_dim(Publisher="Pub1", Platform="Plat1"),
        metric=metrics["no_license"],
    )
    AccessLogFactory(
        import_batch=ib2,
        date="2020-04-01",
        value=5,
        target=targets["target1"],
        item=items["item12"],
        **ir_dim(Publisher="Pub1", Platform="Plat1"),
        metric=metrics["total_item_requests"],
    )
    AccessLogFactory(
        import_batch=ib2,
        date="2020-04-01",
        value=7,
        target=targets["target1"],
        item=items["item12"],
        **ir_dim(Publisher="Pub1", Platform="Plat1"),
        metric=metrics["no_license"],
    )
    AccessLogFactory(
        import_batch=ib2,
        date="2020-04-01",
        value=31,
        item=items["item31"],
        **ir_dim(Publisher="Pub1", Platform="Plat1"),
        metric=metrics["total_item_requests"],
    )
    AccessLogFactory(
        import_batch=ib2,
        date="2020-04-01",
        value=37,
        item=items["item31"],
        **ir_dim(Publisher="Pub1", Platform="Plat1"),
        metric=metrics["unique_item_requests"],
    )

    # before
    AccessLogFactory(
        import_batch=ib3,
        date="2019-12-01",
        value=11,
        target=targets["target1"],
        item=items["item11"],
        **ir_dim(Publisher="Pub1", Platform="Plat1"),
        metric=metrics["total_item_requests"],
    )
    AccessLogFactory(
        import_batch=ib3,
        date="2019-12-01",
        value=13,
        target=targets["target1"],
        item=items["item12"],
        **ir_dim(Publisher="Pub1", Platform="Plat1"),
        metric=metrics["no_license"],
    )

    # after
    AccessLogFactory(
        import_batch=ib4,
        date="2021-01-01",
        value=17,
        target=targets["target1"],
        item=items["item11"],
        **ir_dim(Publisher="Pub1", Platform="Plat1"),
        metric=metrics["no_license"],
    )
    AccessLogFactory(
        import_batch=ib4,
        date="2021-01-01",
        value=19,
        target=targets["target1"],
        item=items["item12"],
        **ir_dim(Publisher="Pub1", Platform="Plat1"),
        metric=metrics["total_item_requests"],
    )

    return ib1, ib2, ib3, ib4
