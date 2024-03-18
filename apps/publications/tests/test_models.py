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
