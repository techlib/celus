from datetime import date
from random import randint

import factory
from dateutil.relativedelta import relativedelta

from faker import Faker

from celus_nigiri.counter5 import CounterRecord

fake = Faker()


def create_title_ids():
    return {'Print_ISSN': '1234-5678', 'ISBN': '9780471397120'}


def create_dim_data(obj):
    return []


class CounterRecordFactory(factory.Factory):
    class Meta:
        model = CounterRecord

    start = factory.LazyFunction(lambda: date(randint(2010, 2021), randint(1, 12), 1))
    end = factory.LazyAttribute(lambda x: x.start + relativedelta(months=1) - relativedelta(days=1))
    metric = factory.LazyFunction(lambda: f'Metric {fake.pyint()}')
    value = factory.Faker('random_int')
    dimension_data = factory.LazyAttribute(create_dim_data)
    title = factory.Faker('sentence')
    title_ids = factory.LazyFunction(create_title_ids)
