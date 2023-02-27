from random import random

import factory.fuzzy
import faker
from django.core.files.base import ContentFile
from publications.models import PlatformTitle, Title, TitleOverlapBatch, TitleOverlapBatchState

from test_fixtures.entities.organizations import OrganizationFactory
from test_fixtures.entities.platforms import PlatformFactory
from test_fixtures.entities.users import UserFactory

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

    name = factory.Faker('sentence')
    isbn = maybe_blank(fake.isbn13, fn_kwargs={"separator": ""})
    issn = maybe_blank(fake.bothify, fn_kwargs={"text": "####-####"})
    eissn = maybe_blank(fake.bothify, fn_kwargs={"text": "####-####"})
    pub_type = factory.fuzzy.FuzzyChoice(Title.PUB_TYPE_MAP.keys())


class PlatformTitleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PlatformTitle

    platform = factory.SubFactory(PlatformFactory)
    organization = factory.SubFactory(OrganizationFactory)
    title = factory.SubFactory(TitleFactory)
    date = factory.Faker('date_this_century')


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
            return ''

        with open(extracted, 'rb') as f:
            data_file = ContentFile(f.read())
            data_file.name = "test.csv"
        obj.source_file = data_file
        return data_file
