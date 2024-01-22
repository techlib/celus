from random import random

import factory
import factory.fuzzy
import faker
from core.fake_data import UserFactory
from django.core.files.base import ContentFile
from organizations.fake_data import OrganizationFactory

from publications.models import (
    Platform,
    PlatformTitle,
    Title,
    TitleOverlapBatch,
    TitleOverlapBatchState,
)

fake = faker.Faker(locale="cs")


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
    isbn = maybe_blank(fake.isbn13, fn_kwargs={"separator": ""})
    issn = maybe_blank(fake.bothify, fn_kwargs={"text": "####-####"})
    eissn = maybe_blank(fake.bothify, fn_kwargs={"text": "####-####"})
    pub_type = factory.fuzzy.FuzzyChoice(Title.PUB_TYPE_MAP.keys())


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
