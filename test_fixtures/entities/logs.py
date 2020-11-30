import factory

from logs.models import ImportBatch


class ImportBatchFactory(factory.DjangoModelFactory):
    class Meta:
        model = ImportBatch
