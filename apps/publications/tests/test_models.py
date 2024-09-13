from datetime import datetime, timedelta

import pytest
from core.fake_data import DataSourceFactory
from core.models import DataSource
from organizations.fake_data import OrganizationFactory

from publications.fake_data import PlatformFactory
from publications.models import Author


@pytest.mark.django_db
class TestPlatformModel:
    @pytest.mark.parametrize(
        "platform_name,organization_name,result",
        (
            ("", None, ""),
            ("ÁBČĎÉFGH", None, "ábčďéfgh"),
            ("ŽÝXWVÚŤŠ", "ÁBČĎÉFGH", "ábčďéfgh.žýxwvúťš"),
            ("/xx/xxx/", None, "xxxxx"),
            ("/yy/yyy/", "xxx/xxx", "xxxxxx.yyyyy"),
            ("xx|xxx", None, "xxxxx"),
            ("yy|yyy", "xxx|xxx", "xxxxxx.yyyyy"),
            ("xx xxx", None, "xx-xxx"),
            ("yy yyy", "xxx xxx", "xxx-xxx.yy-yyy"),
        ),
    )
    def test_slugified_name(self, platform_name, organization_name, result):
        if organization_name:
            platform = PlatformFactory(
                short_name=platform_name,
                source=DataSourceFactory(
                    organization=OrganizationFactory(short_name=organization_name),
                    type=DataSource.TYPE_ORGANIZATION,
                ),
            )
        else:
            platform = PlatformFactory(
                short_name=platform_name,
                source=DataSourceFactory(
                    organization=None, type=DataSource.TYPE_KNOWLEDGEBASE, token="xxxx"
                ),
            )

        assert platform.slugified_name == result

    @pytest.mark.parametrize(
        "arrival_data,day_diff,next_arrival",
        (
            pytest.param(([10.0], [1.0]), 0.0, datetime(2020, 1, 6), id="one-point-50%-0"),
            pytest.param(([10.0], [1.0]), 1.0, datetime(2020, 1, 6), id="one-point-50%-1"),
            pytest.param(([10.0], [1.0]), 5.0, datetime(2020, 1, 8, 12), id="one-point-75%-5"),
            pytest.param(([10.0], [1.0]), 6.0, datetime(2020, 1, 8, 12), id="one-point-75%-6"),
            pytest.param(([10.0], [1.0]), 7.0, datetime(2020, 1, 9), id="one-point-75%-7"),
            pytest.param(([10.0], [1.0]), 8.0, datetime(2020, 1, 10), id="one-point-75%-8"),
            pytest.param(([10.0], [1.0]), 9.0, datetime(2020, 1, 11), id="one-point-75%-9"),
            pytest.param(([10.0], [1.0]), 9.75, datetime(2020, 1, 11, 18), id="one-point-100%-99"),
            pytest.param(([10.0], [1.0]), 10.0, None, id="one-point-None-10.0"),
            pytest.param(
                ([5.0, 20.0], [0.5, 1.0]), 0.0, datetime(2020, 1, 6), id="two-points-50%-0"
            ),
            pytest.param(
                ([5.0, 20.0], [0.5, 1.0]), 1.0, datetime(2020, 1, 6), id="two-points-50%-1"
            ),
            pytest.param(
                ([5.0, 20.0], [0.5, 1.0]), 5.0, datetime(2020, 1, 13, 12), id="two-points-75%-5"
            ),
            pytest.param(
                ([5.0, 20.0], [0.5, 1.0]), 6.0, datetime(2020, 1, 13, 12), id="two-points-75%-6"
            ),
            pytest.param(
                ([5.0, 20.0], [0.5, 1.0]), 12.0, datetime(2020, 1, 14), id="two-points-75%-12"
            ),
            pytest.param(
                ([5.0, 20.0], [0.5, 1.0]),
                12.5,
                datetime(2020, 1, 17, 6),
                id="two-points-87.5%-12.5",
            ),
            pytest.param(
                ([5.0, 20.0], [0.5, 1.0]), 13, datetime(2020, 1, 17, 6), id="two-points-87.5%-13"
            ),
            pytest.param(
                ([5.0, 20.0], [0.5, 1.0]),
                19.75,
                datetime(2020, 1, 21, 18),
                id="two-points-100%-19.75",
            ),
            pytest.param(([5.0, 20.0], [0.5, 1.0]), 20.1, None, id="two-points-None-20.1"),
            pytest.param(None, 0.0, datetime(2020, 1, 4), id="default-50%-0.0"),
            pytest.param(None, 3.0, datetime(2020, 1, 14), id="default-75%-4.0"),
            pytest.param(None, 13.0, datetime(2020, 1, 18, 18), id="default-87.5%-13.0"),
            pytest.param(None, 17.75, datetime(2020, 1, 26), id="default-95%-17.75"),
            pytest.param(None, 25, datetime(2020, 2, 14), id="default-100%-25"),
            pytest.param(None, 44, None, id="default-None-44"),
        ),
    )
    def test_calculate_next_arrival(self, arrival_data, day_diff, next_arrival):
        """Test different arrivals

        Note that when you are using curve it is mapped in a way that
        0 ... 1st day of the month
        1 ... 2nd day of the month

        So the dates might seem moved by 1
        """
        # extract timezone
        harvest_start = datetime.combine(datetime(2020, 1, 1), datetime.min.time())
        current_date = harvest_start + timedelta(days=day_diff)
        if arrival_data:
            platform = PlatformFactory(
                sushi_arrival_stats={"curve": arrival_data[0], "probabs": arrival_data[1]}
            )
        else:
            platform = PlatformFactory(sushi_arrival_stats={})

        assert platform.calculate_next_arrival(harvest_start, current_date) == next_arrival


@pytest.mark.django_db
class TestAuthorModel:
    @pytest.mark.parametrize(
        "in_isni,in_orcid,out_isni,out_orcid",
        (
            ("1", "0", "0000000000000001", "0000000000000000"),
            ("1-1-1-1", "-0-", "0000000000001111", "0000000000000000"),
            ("00000000000000001", "10000000000000000", "0000000000000001", ""),
        ),
    )
    def test_author_ids_normalization(self, in_isni, in_orcid, out_isni, out_orcid):
        author = Author.objects.create(name="foo", isni=in_isni, orcid=in_orcid)

        assert author.isni == out_isni
        assert author.orcid == out_orcid
