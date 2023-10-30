import factory.fuzzy
import faker
from core.fake_data import UserFactory
from django.core.files.base import ContentFile
from publications.fake_data import TitleFactory
from publications.models import Title

from tags.models import (
    AccessibleBy,
    Tag,
    TagClass,
    TaggingAttempt,
    TaggingAttemptOperation,
    TaggingBatch,
    TaggingBatchState,
    TagScope,
    TitleTag,
)

fake = faker.Faker()


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
    name = factory.Sequence(lambda counter: f'tag-{counter:04d}')  # ensures uniqueness
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
    tag_class = None
    tag = factory.LazyAttribute(lambda obj: TagForTitleFactory() if not obj.tag_class else None)
    last_updated_by = factory.SubFactory(UserFactory)
    reprocess_after = None

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


class TaggingAttemptFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TaggingAttempt

    batch = factory.SubFactory(TaggingBatchFactory)
    operation = factory.fuzzy.FuzzyChoice(TaggingAttemptOperation.values)
    success = True
    error = ''
    recognized_columns = factory.LazyFunction(list)
    tag_stats = factory.LazyFunction(dict)
    rows_total = 0
    rows_no_match = 0
    rows_no_tag = 0
    unique_matched_titles = 0
    already_tagged_titles = 0
    tagged_titles = 0
    exclusively_tagged_titles = 0


class TaggingAttemptFuzzyFactory(TaggingAttemptFactory):
    recognized_columns = factory.fuzzy.FuzzyChoice(['issn', 'eissn', 'isbn'])
    tag_stats = factory.lazy_attribute(
        lambda obj: {
            word: {
                'matched_lines': fake.random_int(0, 1000),
                'matched_titles': fake.random_int(0, 1000),
                **(
                    {'tagged_titles': fake.random_int(0, 1000)}
                    if obj.operation == TaggingAttemptOperation.IMPORT
                    else {}
                ),
            }
            for word in fake.words(nb=5)
        }
    )
    rows_total = factory.fuzzy.FuzzyInteger(0, 1000)
    rows_no_match = factory.lazy_attribute(lambda obj: fake.random_int(0, obj.rows_total))
    rows_no_tag = factory.lazy_attribute(lambda obj: fake.random_int(0, obj.rows_total))
    unique_matched_titles = factory.lazy_attribute(lambda obj: fake.random_int(0, obj.rows_total))
    already_tagged_titles = factory.lazy_attribute(lambda obj: fake.random_int(0, obj.rows_total))
    tagged_titles = factory.lazy_attribute(lambda obj: fake.random_int(0, obj.rows_total))
    exclusively_tagged_titles = factory.lazy_attribute(
        lambda obj: fake.random_int(0, obj.rows_total)
    )
