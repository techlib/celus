from random import random

import factory
import factory.fuzzy
import faker
from core.fake_data import UserFactory
from django.core.files.base import ContentFile
from organizations.fake_data import OrganizationFactory

from publications.models import (
    Author,
    AuthorToItem,
    Item,
    Platform,
    PlatformTitle,
    Title,
    TitleOverlapBatch,
    TitleOverlapBatchState,
)

fake = faker.Faker(locale="cs")


class DoiProvider(faker.providers.BaseProvider):
    def doi(self) -> str:
        namespace = self.random_number(digits=5, fix_len=False) + 1000  # 1000 is min
        suffix = self.bothify(text="????-###")
        return f"10.{namespace}/{suffix}"


fake.add_provider(DoiProvider)


class IsniProvider(faker.providers.BaseProvider):
    def isni(self) -> str:
        if self.random_number(1):
            return self.numerify("####-####-####-####")
        else:
            return self.numerify("####-####-####-###X")


fake.add_provider(IsniProvider)


def decide(fn, value, likelihood=0.5, fn_kwargs=None):
    def x():
        kwargs = fn_kwargs or {}
        return fn(**kwargs) if random() <= likelihood else value

    return factory.LazyFunction(x)


def optional(fn, likelihood=0.5, fn_kwargs=None):
    return decide(fn, None, likelihood=likelihood, fn_kwargs=fn_kwargs)


def maybe_blank(fn, likelihood=0.5, fn_kwargs=None):
    return decide(fn, "", likelihood=likelihood, fn_kwargs=fn_kwargs)


class TitleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Title
        django_get_or_create = ("name", "isbn")

    name = factory.Faker("sentence")
    doi = maybe_blank(fake.doi)
    isbn = maybe_blank(fake.isbn13, fn_kwargs={"separator": ""})
    issn = maybe_blank(fake.bothify, fn_kwargs={"text": "####-####"})
    eissn = maybe_blank(fake.bothify, fn_kwargs={"text": "####-####"})
    pub_type = factory.fuzzy.FuzzyChoice(Title.PUB_TYPE_MAP.keys())


class AuthorFactory(factory.django.DjangoModelFactory):
    name = factory.Faker("sentence")
    isni = maybe_blank(fake.doi)
    orcid = maybe_blank(fake.doi)

    class Meta:
        model = Author


class ItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Item
        django_get_or_create = ("name", "doi")

    name = factory.Faker("sentence")
    doi = maybe_blank(fake.doi)
    isbn = maybe_blank(fake.isbn13, fn_kwargs={"separator": ""})
    issn = maybe_blank(fake.bothify, fn_kwargs={"text": "####-####"})
    eissn = maybe_blank(fake.bothify, fn_kwargs={"text": "####-####"})

    @factory.post_generation
    def authors(obj, create, extracted, **kwargs):  # noqa - obj name is ok here
        if not create:
            return
        if extracted:
            for position, author in enumerate(extracted):
                AuthorToItem.objects.get_or_create(position=position, author=author, item=obj)


class AuthorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Author

    isni = maybe_blank(fake.isni)
    orcid = maybe_blank(fake.isni)


class PlatformFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Platform
        django_get_or_create = ("short_name", "source")

    ext_id = factory.Sequence(lambda n: n)
    name = factory.Faker("name")
    short_name = factory.LazyAttribute(lambda x: x.name[:10])
    url = factory.Faker("url")
    source = None


class PlatformTitleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PlatformTitle

    platform = factory.SubFactory(PlatformFactory)
    organization = factory.SubFactory(OrganizationFactory)
    title = factory.SubFactory(TitleFactory)
    date = factory.Faker("date_this_century")


class TitleOverlapBatchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TitleOverlapBatch

    state = TitleOverlapBatchState.INITIAL
    processing_info = factory.LazyFunction(dict)
    last_updated_by = factory.SubFactory(UserFactory)
    organization = None

    @factory.post_generation
    def source_file(obj, create, extracted, **kwargs):  # noqa - name obj is ok here
        """
        We accept a normal file here and preprocess it into ContentFile for convenience
        """
        if not extracted:
            return ""

        with open(extracted, "rb") as f:
            data_file = ContentFile(f.read())
            data_file.name = "test.csv"
        obj.source_file = data_file
        return data_file
