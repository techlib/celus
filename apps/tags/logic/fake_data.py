import factory.fuzzy
from django.core.files.base import ContentFile

from publications.logic.fake_data import TitleFactory
from publications.models import Title
from tags.models import (
    AccessibleBy,
    Tag,
    TagClass,
    TagScope,
    TaggingBatch,
    TaggingBatchState,
    TitleTag,
)
from test_fixtures.entities.users import UserFactory


class TagClassFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TagClass

    name = factory.Faker('word')
    internal = factory.Faker('boolean')
    scope = factory.fuzzy.FuzzyChoice(TagScope.values)
    text_color = factory.Faker('safe_hex_color')
    bg_color = factory.Faker('safe_hex_color')
    desc = factory.Faker('sentence')
    can_modify = AccessibleBy.CONS_ADMINS
    can_create_tags = AccessibleBy.EVERYBODY
    default_tag_can_see = AccessibleBy.EVERYBODY
    default_tag_can_assign = AccessibleBy.EVERYBODY
    owner = None
    owner_org = None
    exclusive = False


class TagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tag
        django_get_or_create = ('tag_class', 'name')

    tag_class = factory.SubFactory(TagClassFactory)
    name = factory.Faker('word')
    text_color = factory.Faker('safe_hex_color')
    bg_color = factory.Faker('safe_hex_color')
    desc = factory.Faker('sentence')
    can_see = AccessibleBy.EVERYBODY
    can_assign = AccessibleBy.EVERYBODY
    owner = None
    owner_org = None


class TagForTitleFactory(TagFactory):

    tag_class = factory.SubFactory(TagClassFactory, scope=TagScope.TITLE)


class TitleTagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TitleTag
        django_get_or_create = ('tag', 'target')

    tag = factory.SubFactory(TagForTitleFactory)
    target = factory.SubFactory(TitleFactory)
    _exclusive = factory.LazyAttribute(lambda obj: obj.tag.tag_class.exclusive)
    _tag_class = factory.LazyAttribute(lambda obj: obj.tag.tag_class)


class TitleTagFactoryExistingTitles(factory.django.DjangoModelFactory):
    class Meta:
        model = TitleTag
        django_get_or_create = ('tag', 'target_id')

    tag = factory.SubFactory(TagForTitleFactory)
    target_id = factory.fuzzy.FuzzyChoice(Title.objects.all().values_list('pk', flat=True))
    _exclusive = factory.LazyAttribute(lambda obj: obj.tag.tag_class.exclusive)
    _tag_class = factory.LazyAttribute(lambda obj: obj.tag.tag_class)


class TaggingBatchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TaggingBatch

    state = TaggingBatchState.INITIAL
    preflight = factory.LazyFunction(dict)
    tag_class = None
    last_updated_by = factory.SubFactory(UserFactory)

    @factory.post_generation
    def tag(obj, create, extracted, **kwargs):  # noqa - name obj is ok here
        # create tag if it should be there
        if (
            obj.state
            in (TaggingBatchState.IMPORTED, TaggingBatchState.IMPORTING, TaggingBatchState.FAILED)
            and not extracted
            and not obj.tag_class
        ):
            obj.tag = TagForTitleFactory.create()
        else:
            obj.tag = extracted
        return obj.tag

    @factory.post_generation
    def source_file(obj, create, extracted, **kwargs):  # noqa - name obj is ok here
        """
        We accept a normal file here and preprocess it into ContentFile for convenience
        """
        if not extracted:
            return ''

        with open(extracted, 'rb') as f:
            data_file = ContentFile(f.read())
            data_file.name = f"test.csv"
        obj.source_file = data_file
        return data_file
