import pytest
from logs.fake_data import InterestGroupFactory
from logs.models import Dimension, InterestDimensionValueMapping, ReportType, ReportTypeToDimension

from ..models import Platform, Title


@pytest.fixture
def platforms():
    p1 = Platform.objects.create(short_name="Plat1", name="Platform 1")
    p2 = Platform.objects.create(
        short_name="Plat2",
        name="Platform 2",
        provider="Provider X",
        url="https://platfrom.provider.test/",
    )
    yield [p1, p2]


@pytest.fixture
def platform():
    return Platform.objects.create(short_name="Platform1", name="Platform 1", provider="Provider 1")


@pytest.fixture
def titles():
    t1 = Title.objects.create(
        name="Title 1",
        pub_type="B",
        isbn="123-464-2356",
        doi="10.1223/x",
        proprietary_ids=["foo:123", "bar:456"],
    )
    t2 = Title.objects.create(
        name="Title 2", pub_type="J", issn="1234-5678", eissn="2345-6789", doi="10.1234/y"
    )
    t3 = Title.objects.create(name="Title 1", pub_type="B", isbn="123-464-666")
    yield [t1, t2, t3]


@pytest.fixture
def interest_rt():
    irt = ReportType.objects.create(short_name="interest")
    for i, dim in enumerate(
        ["Original_Report_Type", "Original_Metric", "Access_Type", "Access_Method"]
    ):
        interest_type_dim, _ = Dimension.objects.get_or_create(short_name=dim)
        rtd = ReportTypeToDimension.objects.create(
            report_type=irt, dimension=interest_type_dim, position=i
        )
        # create default mapping for access type and access method
        if dim in ["Access_Type", "Access_Method"]:
            InterestDimensionValueMapping.objects.create(
                interest_rtdim=rtd,
                source_rtdim=None,  # default mapping
                default_value="Controlled" if dim == "Access_Type" else "Normal",
            )
    return irt


@pytest.fixture
def interest_groups():
    igs = [
        InterestGroupFactory(
            short_name="full_text", name="Full Text", position=1, implies_availability=True
        ),
        InterestGroupFactory(
            short_name="search", name="Search", position=2, implies_availability=True
        ),
        InterestGroupFactory(
            short_name="full_text_denial",
            name="Denial - full text",
            position=4,
            implies_availability=False,
        ),
        InterestGroupFactory(
            short_name="search_denial",
            name="Denial - search",
            position=7,
            implies_availability=False,
        ),
        InterestGroupFactory(
            short_name="other", name="Other", position=10, implies_availability=True
        ),
        InterestGroupFactory(
            short_name="multimedia", name="Multimedia", position=11, implies_availability=True
        ),
    ]
    yield {ig.short_name: ig for ig in igs}
