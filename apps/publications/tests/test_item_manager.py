from collections import Counter

import pytest
from celus_nigiri.record import Author as NigiriAuthor
from logs.fake_data import CounterRecordFactory

from publications.logic.item_management import ItemManager, ItemRec
from publications.logic.validation import normalize_isbn, normalize_title
from publications.models import Author, AuthorToItem, Item


@pytest.mark.django_db
class TestItemManager:
    @pytest.mark.parametrize(["reverse"], [(True,), (False,)])  # reverses order of items bellow
    @pytest.mark.parametrize(
        ["db_item", "db_authors", "in_item", "in_authors", "merge"],
        [
            pytest.param({"name": "AAA"}, [], {"name": "AAA"}, [], True, id="simple name match"),
            pytest.param(
                {"name": "AAA"}, [], {"name": "BBB"}, [], False, id="simple name mismatch"
            ),
            # at least one matching ID is required
            pytest.param(
                {"name": "AAA", "isbn": "978-3-16-148410-0"},
                [],
                {"name": "AAA"},
                [],
                False,
                id="incoming has no matching ID",
            ),
            pytest.param(
                {"name": "AAA", "isbn": "978-3-16-148410-0"},
                [],
                {"name": "AAA", "isbn": "978-3-16-148410-0"},
                [],
                True,
                id="matching name and isbn",
            ),
            # one matching ID should be enough
            pytest.param(
                {"name": "AAA", "isbn": "978-3-16-148410-0"},
                [],
                {"name": "AAA", "isbn": "978-3-16-148410-0", "doi": "xxx"},
                [],
                True,
                id="matching name and isbn with extra id",
            ),
            pytest.param(
                {"name": "AAA", "isbn": "978-3-16-148410-0", "doi": "xxx"},
                [],
                {"name": "AAA", "isbn": "978-3-16-148410-0", "issn": "1111-2222"},
                [],
                True,
                id="matching name and isbn with extra id on both sides",
            ),
            # no mismatch between IDs is allowed
            pytest.param(
                {"name": "AAA", "isbn": "978-3-16-148410-0", "doi": "xxx"},
                [],
                {"name": "AAA", "isbn": "978-3-16-148410-0", "doi": "yyy"},
                [],
                False,
                id="clashing ids even though the rest matches",
            ),
            # proprietary IDs may also serve for matching
            pytest.param(
                {"name": "AAA", "proprietary_ids": ["XXX"]},
                [],
                {"name": "AAA", "proprietary_ids": ["XXX"]},
                [],
                True,
                id="match based on proprietary id",
            ),
            pytest.param(
                {"name": "AAA", "isbn": "978-3-16-148410-0", "proprietary_ids": ["XXX"]},
                [],
                {"name": "AAA", "proprietary_ids": ["XXX"]},
                [],
                True,
                id="match on proprietary id with extra id on one side",
            ),
            # mismatching proprietary IDs are no problem if other ids match
            pytest.param(
                {"name": "AAA", "isbn": "978-3-16-148410-0", "proprietary_ids": ["XXX"]},
                [],
                {"name": "AAA", "isbn": "978-3-16-148410-0", "proprietary_ids": ["YYY"]},
                [],
                True,
                id="matching name and id with mismatch in proprietary ids",
            ),
            # matching proprietary IDs do not "save it" when other IDs mismatch
            pytest.param(
                {"name": "AAA", "isbn": "978-3-16-148410-0", "proprietary_ids": ["XXX"]},
                [],
                {"name": "AAA", "isbn": "978-1-4028-9462-6", "proprietary_ids": ["XXX"]},
                [],
                False,
                id="matching name and proprietary id with mismatch in other id",
            ),
            # uris merge - one way
            pytest.param(
                {"name": "AAA", "isbn": "978-3-16-148410-0"},
                [],
                {"name": "AAA", "isbn": "978-3-16-148410-0", "uris": ["https://aaa.bb/"]},
                [],
                True,
                id="one way uris merge",
            ),
            # uris merge - two way
            pytest.param(
                {"name": "AAA", "isbn": "978-3-16-148410-0", "uris": ["https://bbb.aa/"]},
                [],
                {"name": "AAA", "isbn": "978-3-16-148410-0", "uris": ["https://aaa.bb/"]},
                [],
                True,
                id="two way uris merge",
            ),
            # isbn normalization
            pytest.param(
                {"name": "AAA", "isbn": "978-3-16-148410-0"},
                [],
                {"name": "AAA", "isbn": "9783161484100"},
                [],
                True,
                id="isbn normalization",
            ),
            # item normalization
            pytest.param(
                {"name": "AAA  BBB", "isbn": "978-3-16-148410-0"},
                [],
                {"name": "AAA BBB", "isbn": "978-3-16-148410-0"},
                [],
                True,
                id="item normalization",
            ),
            # case insensitive merging
            pytest.param(
                {"name": "NATURE", "isbn": "978-3-16-148410-0"},
                [],
                {"name": "Nature", "isbn": "978-3-16-148410-0"},
                [],
                True,
                id="case insensitive item",
            ),
            # item only based match with one proprietary ID
            pytest.param(
                {"name": "Nature", "proprietary_ids": []},
                [],
                {"name": "Nature", "proprietary_ids": ["foo"]},
                [],
                False,
                id="item only based match with one empty prop id",
            ),
            # item only based match with no proprietary ID
            pytest.param(
                {"name": "Nature"}, [], {"name": "Nature"}, [], True, id="item only based match"
            ),
            # item + proprietary ID
            pytest.param(
                {"name": "Nature", "proprietary_ids": ["bar"]},
                [],
                {"name": "Nature", "proprietary_ids": ["foo"]},
                [],
                False,
                id="item only based match - prop id mismatch",
            ),
            # item + proprietary IDs with different order
            pytest.param(
                {"name": "Nature", "proprietary_ids": ["bar", "foo"]},
                [],
                {"name": "Nature", "proprietary_ids": ["foo", "bar"]},
                [],
                True,
                id="item only based match - proprietary ids different order",
            ),
            # item + proprietary IDs subset
            pytest.param(
                {"name": "Nature", "proprietary_ids": ["bar", "foo"]},
                [],
                {"name": "Nature", "proprietary_ids": ["foo"]},
                [],
                True,
                id="same item + one set of proprietary ids is subset of other",
            ),
            # item + proprietary IDs with an intersection
            pytest.param(
                {"name": "Nature", "proprietary_ids": ["bar", "foo"]},
                [],
                {"name": "Nature", "proprietary_ids": ["foo", "boo"]},
                [],
                True,
                id="name item + sets of proprietary ids have intersection",
            ),
            # item + proprietary IDs subset + other ids on one side - real life Nature from SD
            pytest.param(
                {"name": "Nature", "proprietary_ids": ["SN:41586"]},
                [],
                {
                    "name": "Nature",
                    "proprietary_ids": [
                        "EBSCOhost:KBID:50974",
                        "ProQuest:40569",
                        "SN:41586",
                        "gale:0359",
                    ],
                    "issn": "0028-0836",
                    "eissn": "1476-4687",
                    "doi": "10.1038/41586.1476-4687",
                },
                [],
                True,
                id="same item + one set of proprietary ids is subset of other + other ids are "
                "present on one side",
            ),
            # item + different IDs
            pytest.param(
                {"name": "Nature", "proprietary_ids": ["bar"], "issn": "1234-5678"},
                [],
                {"name": "Nature", "isbn": "978-3-16-148410-0"},
                [],
                False,
                id="same item but no matching ids",
            ),
            # item + different publication dates
            pytest.param(
                {"name": "Nature", "publication_date": "2022-01-01", "issn": "1234-5678"},
                [],
                {"name": "Nature", "publication_date": "2021-01-01", "issn": "1234-5678"},
                [],
                False,
                id="same name and other id, but different publication dates",
            ),
            # strange thing seen in production
            pytest.param(
                {
                    "name": "Sakarya Üniversitesi İlahiyat Fakültesi Dergisi (SAUIFD)",
                    "issn": "2146-9806",
                    "eissn": "1304-6535",
                    "proprietary_ids": [],
                },
                [],
                {
                    "name": "Sakarya Üniversitesi İlahiyat Fakültesi Dergisi (SAUIFD)",
                    "issn": "2146-9806",
                    "eissn": "1304-6535",
                    "proprietary_ids": ["EBSCOhost:KBID:898430"],
                },
                [],
                True,
                id="turkish I problem",
            ),
            pytest.param(
                {"name": "Nature", "publication_date": "2021-01-01"},
                [{"name": "A1"}],
                {"name": "Nature", "publication_date": "2021-01-01"},
                [{"name": "A2"}],
                False,
                id="same publication date, but different authors => new",
            ),
            pytest.param(
                {"name": "Nature", "publication_date": "2021-01-01"},
                [{"name": "A1"}, {"name": "A2"}],
                {"name": "Nature", "publication_date": "2022-01-01"},
                [{"name": "A1"}, {"name": "A2"}],
                False,
                id="same authors, diffrent publication date => new",
            ),
            pytest.param(
                {"name": "Nature", "publication_date": "2021-01-01"},
                [{"name": "A1"}, {"name": "A2"}],
                {"name": "Nature", "publication_date": "2021-01-01"},
                [{"name": "A1"}, {"name": "A2"}],
                True,
                id="same authors, same publication date => merge",
            ),
            pytest.param(
                {"name": "Nature"},
                [{"name": "A2"}, {"name": "A1"}],
                {"name": "Nature"},
                [{"name": "A1"}, {"name": "A2"}],
                False,
                id="different authors order => new",
            ),
            pytest.param(
                {"name": "Nature"},
                [{"name": "A1"}, {"name": "A2"}, {"name": "A3"}],
                {"name": "Nature"},
                [{"name": "A1"}, {"name": "A2"}],
                False,
                id="extra authors => new",
            ),
            pytest.param(
                {"name": "Nature"},
                [{"name": "A1"}, {"name": "A2"}],
                {"name": "Nature"},
                [{"name": "A1"}, {"name": "A2", "ORCID": "1234123412341234"}],
                False,
                id="author with extra ORCID identifier => new",
            ),
            pytest.param(
                {"name": "Nature"},
                [{"name": "A1"}, {"name": "A2", "isni": "1234123412341234"}],
                {"name": "Nature"},
                [{"name": "A1"}, {"name": "A2"}],
                False,
                id="author with extra ISNI identifier => new",
            ),
            pytest.param(
                {"name": "Nature", "publication_date": "2021-01-01"},
                [{"name": "A1"}, {"name": "A2"}],
                {"name": "Nature"},
                [{"name": "A1"}, {"name": "A2"}],
                False,
                id="same authors extra publication date => new",
            ),
            pytest.param(
                {"name": "Nature", "issn": "1234-5678"},
                [{"name": "A1"}, {"name": "A2"}],
                {"name": "Nature"},
                [{"name": "A1"}, {"name": "A2"}],
                False,
                id="same authors extra issn => merge",
            ),
        ],
    )
    def test_get_or_create_merging_strategy(
        self,
        db_item: dict,
        db_authors: list,
        in_item: dict,
        in_authors: list,
        merge: bool,
        reverse: bool,
    ):
        if reverse:
            # switch db_item <-> in_item because the result should not depend on the order
            # of imports, so we get some extra testing for free and do not need to create
            # reversed tests manually
            db_item, in_item = in_item, db_item
        # prepare the db_item in the database as if it were imported before
        db_item = dict(db_item)  # create copy not to change it for the following run if modified
        # the following would normally happen on first import of the item
        db_item["name"] = normalize_title(db_item["name"])
        if "uris" in db_item:
            # uris is stored in an array, so we need to wrap it here
            db_item["uris"] = db_item.pop("uris")
        if "isbn" in db_item:
            # this would normally happen on first import of the item
            db_item["isbn"] = normalize_isbn(db_item["isbn"])
        item = Item.objects.create(**db_item)
        assert Item.objects.count() == 1

        # Create and link authors
        for idx, author in enumerate(db_authors):
            author_obj = Author.objects.create(**author)
            AuthorToItem.objects.create(position=idx, item=item, author=author_obj)

        # now process the in_item
        item_rec = ItemRec(**in_item)
        item_rec.authors = [NigiriAuthor(**e) for e in in_authors]

        assert isinstance(item_rec.proprietary_ids, set)
        im = ItemManager()
        # the following is necessary because normalization would normally be carried out
        # in `counter_record_to_item_rec` which we do not use here
        im.prefetch_items([item_rec])
        im.get_or_create(item_rec)
        if merge:
            assert Item.objects.count() == 1, "items should be merged"
            # compare all different IDs and check they were merged from both records
            item = Item.objects.get()
            for id_attr in "isbn", "issn", "eissn", "doi":
                # id_attrs should be merged
                exp_value = db_item.get(id_attr, "") or in_item.get(id_attr, "")
                if id_attr == "isbn":
                    exp_value = normalize_isbn(exp_value)
                assert getattr(item, id_attr) == exp_value, (
                    f'{id_attr} is DB should be "{exp_value}"'
                )
            assert set(item.proprietary_ids) == set(db_item.get("proprietary_ids", "")) | set(
                in_item.get("proprietary_ids", [])
            )
            assert set(item.uris) == set(
                filter(None, db_item.get("uris", []) + in_item.get("uris", []))
            )
            # check that when reimporting the same in_record that it does not hit database again
            # (this checks that the pre-fetched data in ItemManager are properly updated on merge)
            im.stats = Counter()
            im.get_or_create(item_rec)
            assert im.stats["existing"] == 1, "the reimported item should be there in full"
        else:
            assert Item.objects.count() == 2, "items should not be merged"

    @pytest.mark.parametrize(
        ["db_pub_type", "in_pub_type", "expected_pub_type"],
        [
            (Item.PUB_TYPE_UNKNOWN, Item.PUB_TYPE_ARTICLE, Item.PUB_TYPE_ARTICLE),
            (Item.PUB_TYPE_ARTICLE, Item.PUB_TYPE_UNKNOWN, Item.PUB_TYPE_ARTICLE),
            (Item.PUB_TYPE_UNKNOWN, Item.PUB_TYPE_UNKNOWN, Item.PUB_TYPE_UNKNOWN),
            (Item.PUB_TYPE_ARTICLE, Item.PUB_TYPE_BOOK_SEGMENT, Item.PUB_TYPE_ARTICLE),
        ],
    )
    def test_pub_type_upgrade(self, db_pub_type, in_pub_type, expected_pub_type):
        item = Item.objects.create(name="AAA", doi="10.1234/foo", pub_type=db_pub_type)
        item_rec = ItemRec(name="AAA", doi="10.1234/foo", pub_type=in_pub_type)
        im = ItemManager()
        im.prefetch_items([item_rec])
        new_pk = im.get_or_create(item_rec)
        assert new_pk == item.pk
        item.refresh_from_db()
        assert item.pub_type == expected_pub_type

    def test_get_or_create(self):
        """
        Creating same item
        """
        im = ItemManager()
        record = ItemRec(name="ITEM", isbn="977-481-83-13d6-2")

        # creating same item
        pk1 = im.get_or_create(record)
        assert im.stats["created"] == 1
        assert im.stats["existing"] == 0
        pk2 = im.get_or_create(record)
        assert im.stats["created"] == 1
        assert im.stats["existing"] == 1
        assert pk1 is not None
        assert pk2 is not None
        assert pk1 == pk2

    def test_get_or_create_with_two_winners(self):
        """
        Test a real-world situation where there are two matching candidates in the DB.

        The challenge here is that if we pick the wrong one and then 'upgrade it' using the
        data from the incoming data, it would start clashing with the other record, which we
        need to avoid.
        """
        Item.objects.create(name="A", issn="1111-2222")
        i2 = Item.objects.create(name="A", issn="1111-2222", eissn="2222-1111")

        im = ItemManager()
        record = ItemRec(name="A", issn="1111-2222", eissn="2222-1111")
        im.prefetch_items([record])
        pk = im.get_or_create(record)
        assert im.stats["existing"] == 1, "find existing, not upgrade other if we don't have to"
        assert pk == i2.pk

    def test_get_or_create_same_score_same_ordering(self):
        """
        Test a situation when two items have exactly the same score.

        In this case the older item (with lower pk) should be picked.
        Note that this test was added to aviod non-deterministic result
        based on db sorting.
        """
        Item.objects.create(name="A", doi="https://x/", eissn="2222-1111")
        item = Item.objects.create(name="A", issn="1111-2222", doi="https://x/")
        Item.objects.create(name="A", issn="1111-2222", eissn="2222-1111")

        im = ItemManager()
        record = ItemRec(name="A", issn="1111-2222")
        pk = im.get_or_create(record)
        assert im.stats["existing"] == 1, "find existing, not upgrade other if we don't have to"
        assert pk == item.pk, "oldest item with highest score was picked"

    @pytest.mark.parametrize(
        ["item_rec", "first", "second", "third", "which"],
        [
            pytest.param(
                {"name": "A", "issn": "1111-2222", "eissn": "2222-1111"},
                {"name": "A", "issn": "1111-2222"},
                {"name": "A", "issn": "1111-2222", "eissn": "2222-1111"},
                {"name": "A", "issn": "1111-2222", "eissn": "2222-1111", "doi": "https://x/"},
                2,
                id="match the one with extra ids",
            ),
            pytest.param(
                {"name": "A", "issn": "1111-2222", "eissn": "2222-1111"},
                {"name": "A", "issn": "1111-2222", "eissn": "2222-1112"},
                {"name": "A", "issn": "2111-2222", "eissn": "2222-1111"},
                {"name": "A", "issn": "2111-2222", "eissn": "2222-1112", "doi": "https://x/"},
                None,
                id="match the one with extra ids",
            ),
            pytest.param(
                {"name": "A", "issn": "1111-2222", "eissn": "2222-1111"},
                {"name": "A", "issn": "2111-2222", "eissn": "2222-1112"},
                {"name": "A", "issn": "1111-2222", "doi": "htts://y/"},
                {"name": "A", "doi": "https://x/", "eissn": "2222-1111"},
                1,
                id="prefer the older with highest score",
            ),
        ],
    )
    def test_get_or_create_with_three(self, item_rec, first, second, third, which):
        items = [
            Item.objects.create(**first),
            Item.objects.create(**second),
            Item.objects.create(**third),
        ]

        im = ItemManager()
        record = ItemRec(**item_rec)
        im.prefetch_items([record])
        pk = im.get_or_create(record)
        if which is None:
            assert pk not in [e.pk for e in items]
            assert im.stats["created"] == 1, "all existing record non-mergable"
        else:
            assert pk == items[which].pk
            assert im.stats["created"] == 0, "nothing created"

    @pytest.mark.parametrize(
        ["ids", "attrs"],
        [
            ({"Print_ISSN": "1111-2222"}, {"issn": "1111-2222"}),
            (
                {"Print_ISSN": "1111-2222", "Proprietary": "FOO"},
                {"issn": "1111-2222", "proprietary_ids": {"FOO"}},
            ),
            # test normalization as well
            (
                {"Print_ISSN": "1111- 2222 ", "Proprietary": " FOO ", "ISBN": "978-3-16-148410-0"},
                {"issn": "1111-2222", "proprietary_ids": {"FOO"}, "isbn": "9783161484100"},
            ),
            # garbage in ISBN
            (
                {
                    "Print_ISSN": "1111- 2222 ",
                    "Proprietary": " FOO ",
                    "ISBN": "978-3-16-148410-0 (print); 978-3-16-148411-1 (ebook)",
                },
                {"issn": "1111-2222", "proprietary_ids": {"FOO"}, "isbn": "9783161484100"},
            ),
            # garbage in ISSN
            (
                {"Print_ISSN": "1111- 2222 (print)", "Proprietary": " FOO "},
                {"issn": "1111-2222", "proprietary_ids": {"FOO"}},
            ),
            (
                {"Print_ISSN": "garbage 1111-2222", "Proprietary": " FOO "},
                {"issn": "1111-2222", "proprietary_ids": {"FOO"}},
            ),
            (
                {"Print_ISSN": "garbagegarbage", "Proprietary": " FOO "},
                {"issn": "garbagega", "proprietary_ids": {"FOO"}},
            ),
        ],
    )
    def test_counter_record_to_item_rec(self, ids, attrs):
        cr = CounterRecordFactory.create(item_ids=ids)
        im = ItemManager()
        item_rec = im.counter_record_to_item_rec(cr)
        for key, value in attrs.items():
            assert getattr(item_rec, key) == value
        for key in ["issn", "eissn", "isbn", "doi", "proprietary_ids", "uris"]:
            if key not in attrs:
                assert not getattr(item_rec, key), "unset attribute should be empty"
