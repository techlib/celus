import factory

from necronomicon.models import Batch, Candidate


class BatchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Batch


class CandidateFactory(factory.django.DjangoModelFactory):
    batch = factory.SubFactory(Batch)

    class Meta:
        model = Candidate
