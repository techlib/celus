from datetime import date

import factory
from dateutil.relativedelta import relativedelta

from sushi.models import SushiFetchAttempt

from .credentials import CredentialsFactory
from .counter_report_types import CounterReportTypeFactory


class FetchAttemptFactory(factory.DjangoModelFactory):
    class Meta:
        model = SushiFetchAttempt

    credentials = factory.SubFactory(CredentialsFactory)
    counter_report = factory.SubFactory(CounterReportTypeFactory)
    credentials_version_hash = factory.LazyAttribute(lambda x: x.credentials.version_hash)

    start_date = date(2020, 1, 1)
    end_date = factory.LazyAttribute(
        lambda x: x.start_date + relativedelta(months=1) - relativedelta(days=1)
    )
