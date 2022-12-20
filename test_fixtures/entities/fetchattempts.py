from datetime import date
from random import randint

import factory
from dateutil.relativedelta import relativedelta
from sushi.models import AttemptStatus, SushiFetchAttempt

from .counter_report_types import CounterReportTypeFactory
from .credentials import CredentialsFactory


class FetchAttemptFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SushiFetchAttempt

    credentials = factory.SubFactory(CredentialsFactory)
    counter_report = factory.SubFactory(CounterReportTypeFactory)
    credentials_version_hash = factory.LazyAttribute(lambda x: x.credentials.version_hash)

    start_date = factory.LazyFunction(lambda: date(randint(2010, 2021), randint(1, 12), 1))
    end_date = factory.LazyAttribute(
        lambda x: x.start_date + relativedelta(months=1) - relativedelta(days=1)
    )
    import_batch = None
    status = AttemptStatus.SUCCESS
    data_file = factory.django.FileField()
    file_size = factory.LazyAttribute(
        lambda x: x.data_file.size if hasattr(x.data_file, 'size') else 0
    )
    checksum = factory.LazyAttribute(
        lambda x: SushiFetchAttempt.checksum_fileobj(x.data_file)[0]
        if hasattr(x.data_file, 'seek')
        else 'foobar'
    )
