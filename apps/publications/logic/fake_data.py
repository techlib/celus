from random import random

import factory.fuzzy
import faker

from publications.models import Title

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

    name = factory.Faker('')
    isbn = maybe_blank(fake.isbn13, fn_kwargs={"separator": ""})
    issn = maybe_blank(fake.bothify, fn_kwargs={"text": "####-####"})
    eissn = maybe_blank(fake.bothify, fn_kwargs={"text": "####-####"})
    pub_type = factory.fuzzy.FuzzyChoice(Title.PUB_TYPE_MAP.keys())
