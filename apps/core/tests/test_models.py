import pytest

from test_fixtures.scenarios.basic import *  # noqa


@pytest.mark.django_db
def test_accessible_platforms(basic1):  # noqa
    # master admin can access all platforms
    assert [e for e in basic1["users"]["master"].accessible_platforms()] == sorted(
        basic1["platforms"].values(), key=lambda x: x.name
    )

    assert list(basic1["users"]["admin1"].accessible_platforms()) == [
        basic1["platforms"]["branch"],  # suborganization of root
        basic1["platforms"]["empty"],  # no source => public
        basic1["platforms"]["master"],  # API source => public
        basic1["platforms"]["root"],  # admin of root
        basic1["platforms"]["shared"],  # no source => public
    ]

    assert list(basic1["users"]["admin2"].accessible_platforms()) == [
        basic1["platforms"]["empty"],  # no source => public
        basic1["platforms"]["master"],  # API source => public
        basic1["platforms"]["shared"],  # no source => public
        basic1["platforms"]["standalone"],  # admin of standalone
    ]

    assert list(basic1["users"]["user1"].accessible_platforms()) == [
        basic1["platforms"]["branch"],  # member of branch organization
        basic1["platforms"]["empty"],  # no source => public
        basic1["platforms"]["master"],  # API source => public
        basic1["platforms"]["shared"],  # no source => public
    ]

    assert list(basic1["users"]["user2"].accessible_platforms()) == [
        basic1["platforms"]["empty"],  # no source => public
        basic1["platforms"]["master"],  # API source => public
        basic1["platforms"]["shared"],  # no source => public
        basic1["platforms"]["standalone"],  # member of standalone organization
    ]

    # test with organization defined
    assert list(
        basic1["users"]["user2"].accessible_platforms(basic1["organizations"]["standalone"])
    ) == [
        basic1["platforms"]["empty"],  # no source => public
        basic1["platforms"]["master"],  # API source => public
        basic1["platforms"]["shared"],  # no source => public
        basic1["platforms"]["standalone"],  # member of standalone organization
    ]

    assert list(basic1["users"]["user2"].accessible_platforms(basic1["organizations"]["root"])) == [
        basic1["platforms"]["empty"],  # no source => public
        basic1["platforms"]["master"],  # API source => public
        basic1["platforms"]["shared"],  # no source => public
    ]

    assert list(
        basic1["users"]["admin1"].accessible_platforms(basic1["organizations"]["root"])
    ) == [
        basic1["platforms"]["empty"],  # no source => public
        basic1["platforms"]["master"],  # API source => public
        basic1["platforms"]["root"],  # admin of root
        basic1["platforms"]["shared"],  # no source => public
    ]

    assert list(
        basic1["users"]["admin1"].accessible_platforms(basic1["organizations"]["branch"])
    ) == [
        basic1["platforms"]["branch"],  # suborganization of root
        basic1["platforms"]["empty"],  # no source => public
        basic1["platforms"]["master"],  # API source => public
        basic1["platforms"]["shared"],  # no source => public
    ]
