from functools import lru_cache

import factory.fuzzy

from publications.logic.fake_data import TitleFactory
from publications.models import Title
from tags.models import AccessibleBy, TagClass, Tag, TagScope, TitleTag


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
