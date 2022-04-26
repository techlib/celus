import codecs
import operator
import os
import tempfile
from collections import Counter
from functools import reduce
from typing import BinaryIO, Callable, Optional, Tuple, Type, Union

from colorfield.fields import ColorField
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.files.base import File
from django.db import models
from django.db.models import Q, QuerySet
from django.utils.timezone import now
from django.utils.translation import gettext as _
from rest_framework.exceptions import PermissionDenied

from core.models import CreatedUpdatedMixin, REL_ORG_ADMIN, User
from logs.logic.data_import import TitleManager
from organizations.models import Organization
from publications.models import Platform, Title
from tags.logic.titles_lists import CsvTitleListReader


class AccessibleBy(models.IntegerChoices):
    EVERYBODY = 10, _("Everybody")
    ORG_USERS = 20, _("Organization users")
    ORG_ADMINS = 30, _("Organization admins")
    CONS_ADMINS = 40, _("Consortium admins")
    OWNER = 50, _("Owner")
    SYSTEM = 100, _("System")  # only internal Celus functions can access this

    @classmethod
    def org_related(cls) -> Tuple['AccessibleBy', 'AccessibleBy']:
        return (cls.ORG_USERS, cls.ORG_ADMINS)


class TagScope(models.TextChoices):
    TITLE = 'title', _("Title")
    PLATFORM = 'platform', _("Platform")
    ORGANIZATION = 'organization', _('Organization')


def access_filters(attr_name: str, user: User) -> Q:
    """
    Returns a filter for queryset which applies relevant checks on the `attr_name` attribute
    which is a choice of type `AccessibleBy`
    """
    possibilities = [
        Q(**{attr_name: AccessibleBy.EVERYBODY}),
        Q(**{attr_name: AccessibleBy.OWNER, 'owner': user}),
        Q(**{attr_name: AccessibleBy.ORG_USERS, 'owner_org__in': user.accessible_organizations()}),
        Q(**{attr_name: AccessibleBy.ORG_ADMINS, 'owner_org__in': user.admin_organizations()}),
    ]
    if user.is_superuser or user.is_admin_of_master_organization:
        possibilities.append(Q(**{attr_name: AccessibleBy.CONS_ADMINS}))

    return reduce(operator.or_, possibilities)


class TagClassQuerySet(models.QuerySet):
    def user_accessible_tag_classes(self, user: User) -> QuerySet['TagClass']:
        return self.filter(access_filters('can_create_tags', user))

    def user_modifiable_tag_classes(self, user: User) -> QuerySet['TagClass']:
        return self.filter(access_filters('can_modify', user))


class TagClass(CreatedUpdatedMixin, models.Model):

    internal = models.BooleanField(default=False)
    scope = models.CharField(max_length=16, choices=TagScope.choices)
    name = models.CharField(max_length=200)
    exclusive = models.BooleanField(
        default=False, help_text='An item may be only tagged by one tag from an exclusive tag class'
    )
    text_color = ColorField(default='#303030')
    bg_color = ColorField(default='#E2E2E2')
    desc = models.CharField(max_length=160, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.CASCADE,
        blank=True,
        help_text='When an access level is set to "owner", this specifies the one',
        related_name='owned_tagclasses',
    )
    owner_org = models.ForeignKey(
        Organization,
        null=True,
        on_delete=models.CASCADE,
        blank=True,
        help_text='When an access level is set to "organization users" or "organization admin", '
        'this is the organization',
    )
    can_modify = models.PositiveSmallIntegerField(
        choices=AccessibleBy.choices,
        default=AccessibleBy.OWNER,
        help_text="Who can modify the parameters of this class",
    )
    can_create_tags = models.PositiveSmallIntegerField(
        choices=AccessibleBy.choices,
        default=AccessibleBy.OWNER,
        help_text="Who can create tags of this class",
    )
    default_tag_can_see = models.PositiveSmallIntegerField(
        choices=AccessibleBy.choices,
        default=AccessibleBy.OWNER,
        help_text="Default value for Tag.can_see of tags of this class",
    )
    default_tag_can_assign = models.PositiveSmallIntegerField(
        choices=AccessibleBy.choices,
        default=AccessibleBy.OWNER,
        help_text="Default value for Tag.can_assign of tags of this class",
    )

    objects = TagClassQuerySet.as_manager()

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Tag classes'
        constraints = [
            models.CheckConstraint(
                # owner must be set if can_modify or can_create_tags is set to OWNER
                name='tag_class_owner_not_null',
                check=(
                    (
                        (
                            Q(can_modify=AccessibleBy.OWNER)
                            | Q(can_create_tags=AccessibleBy.OWNER)
                            | Q(default_tag_can_see=AccessibleBy.OWNER)
                            | Q(default_tag_can_assign=AccessibleBy.OWNER)
                        )
                        & Q(owner__isnull=False)
                    )
                    | ~(
                        Q(can_modify=AccessibleBy.OWNER)
                        | Q(can_create_tags=AccessibleBy.OWNER)
                        | Q(default_tag_can_see=AccessibleBy.OWNER)
                        | Q(default_tag_can_assign=AccessibleBy.OWNER)
                    )
                ),
            ),
            models.CheckConstraint(
                # owner_org must be set if can_modify or can_create_tags is set to ORG_*
                # otherwise it must be null
                name='tag_class_owner_org_not_null',
                check=(
                    (
                        (
                            Q(can_create_tags__in=[AccessibleBy.ORG_USERS, AccessibleBy.ORG_ADMINS])
                            | Q(can_modify__in=[AccessibleBy.ORG_USERS, AccessibleBy.ORG_ADMINS])
                            | Q(
                                default_tag_can_see__in=[
                                    AccessibleBy.ORG_USERS,
                                    AccessibleBy.ORG_ADMINS,
                                ]
                            )
                            | Q(
                                default_tag_can_assign__in=[
                                    AccessibleBy.ORG_USERS,
                                    AccessibleBy.ORG_ADMINS,
                                ]
                            )
                        )
                        & Q(owner_org__isnull=False)
                    )
                    | (
                        ~(
                            Q(can_create_tags__in=[AccessibleBy.ORG_USERS, AccessibleBy.ORG_ADMINS])
                            | Q(can_modify__in=[AccessibleBy.ORG_USERS, AccessibleBy.ORG_ADMINS])
                            | Q(
                                default_tag_can_see__in=[
                                    AccessibleBy.ORG_USERS,
                                    AccessibleBy.ORG_ADMINS,
                                ]
                            )
                            | Q(
                                default_tag_can_assign__in=[
                                    AccessibleBy.ORG_USERS,
                                    AccessibleBy.ORG_ADMINS,
                                ]
                            )
                        )
                        & Q(owner_org__isnull=True)
                    )
                ),
            ),
        ]

    def __str__(self):
        return self.name

    @property
    def target_class(self) -> Union[Type[Platform], Type[Title], Type[Organization]]:
        if self.scope == TagScope.TITLE:
            return Title
        elif self.scope == TagScope.PLATFORM:
            return Platform
        elif self.scope == TagScope.ORGANIZATION:
            return Organization
        raise ValueError(f'Unexpected scope "{self.scope}"')

    @classmethod
    def can_set_access_level(
        cls, user: User, level: AccessibleBy, organization: Optional[Organization] = None
    ):
        """
        Returns True if the user can create a tag_class with this access level == `can_create_tags`
        `organization` is used only when level `ORG_ADMINS` or `ORG_USERS` is requested.

        This is how it should work:

        user type   EVERYBODY   ORG_USERS   ORG_ADMINS   CONS_ADMINS   OWNER   SYSTEM
        user                0           0            0             0       1        0
        org_admin           0           1            1             0       1        0
        cons_user           0           0            0             0       1        0
        cons_admin          1           1            1             1       1        0
        superuser           1           1            1             1       1        0

        """
        if level == AccessibleBy.SYSTEM:
            # no one can set SYSTEM access level - this is used only internally
            return False
        if level == AccessibleBy.OWNER:
            # everybody can create a tag_class for personal use
            return True
        if user.is_superuser or user.is_admin_of_master_organization:
            # super user and consortia admin can create any access level
            return True
        if level in AccessibleBy.org_related() and organization:
            if user.organization_relationship(organization.pk) == REL_ORG_ADMIN:
                return True
        return False


class TagQuerySet(models.QuerySet):
    def user_accessible_tags(self, user: User) -> QuerySet['Tag']:
        return self.filter(access_filters('can_see', user))

    def user_assignable_tags(self, user: User) -> QuerySet['Tag']:
        return self.filter(access_filters('can_assign', user))


class Tag(CreatedUpdatedMixin, models.Model):

    tag_class = models.ForeignKey(TagClass, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    text_color = ColorField(default='#303030')
    bg_color = ColorField(default='#E2E2E2')
    desc = models.CharField(max_length=160, blank=True)
    can_see = models.PositiveSmallIntegerField(
        choices=AccessibleBy.choices,
        default=AccessibleBy.OWNER,
        help_text="Who can see the tags on the tagged items",
    )
    can_assign = models.PositiveSmallIntegerField(
        choices=AccessibleBy.choices,
        default=AccessibleBy.OWNER,
        help_text="Who can assign the tags to items",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.CASCADE,
        blank=True,
        help_text='When "can_see" or "can_assign" is set to "owner", this specifies the one',
        related_name='owned_tags',
    )
    owner_org = models.ForeignKey(
        Organization,
        null=True,
        on_delete=models.CASCADE,
        blank=True,
        help_text='When "can_see" or "can_assign" is set to "organization users" or '
        '"organization admins", this is the organization',
    )
    # tagged objects
    titles = models.ManyToManyField(Title, through='TitleTag', related_name='tags')
    platforms = models.ManyToManyField(Platform, through='PlatformTag', related_name='tags')
    organizations = models.ManyToManyField(
        Organization, through='OrganizationTag', related_name='tags'
    )

    # custom manager
    objects = TagQuerySet.as_manager()

    class Meta:
        ordering = ['name']
        constraints = [
            models.CheckConstraint(
                # owner must be set if can_see or can_assign is set to OWNER
                name='tag_owner_not_null',
                check=(
                    (
                        (Q(can_see=AccessibleBy.OWNER) | Q(can_assign=AccessibleBy.OWNER))
                        & Q(owner__isnull=False)
                    )
                    | ~(Q(can_see=AccessibleBy.OWNER) | Q(can_assign=AccessibleBy.OWNER))
                ),
            ),
            models.CheckConstraint(
                # owner_org must be set if can_see or can_assign is set to ORG_*
                # otherwise it must be null
                name='tag_owner_org_not_null',
                check=(
                    (
                        (
                            Q(can_see__in=[AccessibleBy.ORG_USERS, AccessibleBy.ORG_ADMINS])
                            | Q(can_assign__in=[AccessibleBy.ORG_USERS, AccessibleBy.ORG_ADMINS])
                        )
                        & Q(owner_org__isnull=False)
                    )
                    | (
                        ~(
                            Q(can_see__in=[AccessibleBy.ORG_USERS, AccessibleBy.ORG_ADMINS])
                            | Q(can_assign__in=[AccessibleBy.ORG_USERS, AccessibleBy.ORG_ADMINS])
                        )
                        & Q(owner_org__isnull=True)
                    )
                ),
            ),
        ]

    def __str__(self):
        return self.name

    @classmethod
    def link_class_from_target(
        cls, target: Union[Title, Platform, Organization]
    ) -> Type['ItemTag']:
        if isinstance(target, Title):
            return TitleTag
        elif isinstance(target, Platform):
            return PlatformTag
        elif isinstance(target, Organization):
            return OrganizationTag
        raise ValueError(f'unsupported target object of class "{target.__class__}"')

    def tag(self, target: Union[Title, Platform, Organization], user: User) -> 'ItemTag':
        """
        Assigns `self` as tag to `target`. Does check that the user can actually assign `self`.
        To do this, user must be present.
        """
        if self.can_user_assign(user):
            return self._tag(target, user=user)
        else:
            raise PermissionDenied(f'User "{user}" is not allowed to assign tag #{self.pk}')

    def _tag(
        self, target: Union[Title, Platform, Organization], user: Optional[User] = None
    ) -> 'ItemTag':
        """
        Lowlevel method which does not do any checks. Use `tag()` to do permission checks
        """
        if not isinstance(target, self.tag_class.target_class):
            raise ValueError(
                f'Cannot apply tag with scope "{self.tag_class.scope}" to "{target.__class__}"'
            )
        link_cls = self.link_class_from_target(target)
        return link_cls.objects.create(tag=self, target=target, last_updated_by=user)

    def can_user_assign(self, user: User) -> bool:
        return Tag.objects.user_assignable_tags(user).filter(pk=self.pk).exists()


class ItemTag(CreatedUpdatedMixin, models.Model):

    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    target = models.ForeignKey(Title, on_delete=models.CASCADE)  # just to have something here
    tagging_batch = models.ForeignKey(
        'TaggingBatch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='If the tagging was done in a batch, this is the batch',
    )
    # the following is redundant, but we need it for a constraint
    _tag_class = models.ForeignKey(TagClass, on_delete=models.CASCADE)
    _exclusive = models.BooleanField()

    class Meta:
        abstract = True
        unique_together = [('tag', 'target')]
        constraints = [
            models.UniqueConstraint(
                fields=('target', '_tag_class'),
                condition=Q(_exclusive=True),
                name='%(class)s_unique_tag_class_for_exclusive',
            )
        ]

    @classmethod
    def get_subclass_by_item_type(cls, item_type: TagScope) -> Type['ItemTag']:
        if item_type == TagScope.TITLE:
            return TitleTag
        elif item_type == TagScope.PLATFORM:
            return PlatformTag
        elif item_type == TagScope.ORGANIZATION:
            return OrganizationTag
        raise ValueError(f'Unexpected item type "{item_type}"')

    def save(self, **kwargs):
        self._tag_class_id = self.tag.tag_class_id
        self._exclusive = self.tag.tag_class.exclusive
        super().save(**kwargs)


class TitleTag(ItemTag):

    target = models.ForeignKey(Title, on_delete=models.CASCADE)


class PlatformTag(ItemTag):

    target = models.ForeignKey(Platform, on_delete=models.CASCADE)


class OrganizationTag(ItemTag):

    target = models.ForeignKey(Organization, on_delete=models.CASCADE)


def where_to_store(instance: 'TaggingBatch', filename):
    root, ext = os.path.splitext(filename)
    ts = now().strftime('%Y%m%d-%H%M%S.%f')
    return f'tagging_batch/{root}-{ts}{ext}'


class TaggingBatchState(models.TextChoices):
    """
    I originally used `MduState` for this, but needed the `UNDOING` state for the unassigning
    process. Because inheritance is not possible, I had to recreate the whole thing, but kept the
    original names so that I do not have to change the frontend code.
    """

    INITIAL = 'initial', _("Initial")
    PREFLIGHT = 'preflight', _("Preflight")
    IMPORTING = 'importing', _("Importing")
    IMPORTED = 'imported', _("Imported")
    PREFAILED = 'prefailed', _("Preflight failed")
    FAILED = 'failed', _("Import failed")
    UNDOING = 'undoing', _('Undoing')


class TaggingBatch(CreatedUpdatedMixin, models.Model):

    source_file = models.FileField(upload_to=where_to_store, blank=True, null=True, max_length=256)
    annotated_file = models.FileField(
        upload_to='tagging_batch/',
        blank=True,
        null=True,
        max_length=256,
        help_text='File with additional data added during pre-flight or import',
    )
    preflight = models.JSONField(
        default=dict,
        blank=True,
        help_text='Information gathered during the preflight check of the source',
    )
    postflight = models.JSONField(
        default=dict,
        blank=True,
        help_text='Information gathered during the actual processing of the source and '
        'application of tags',
    )
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, blank=True, null=True)
    tag_class = models.ForeignKey(TagClass, on_delete=models.CASCADE, blank=True, null=True)
    state = models.CharField(
        max_length=20, choices=TaggingBatchState.choices, default=TaggingBatchState.INITIAL
    )

    class Meta:
        verbose_name_plural = 'Tagging batches'
        constraints = [
            models.CheckConstraint(
                # either tag or tag_class must be set, but not both, if the state is
                # imported, importing or failed
                # in other cases, we do not care about tag or tag_class
                name='one_of_tag_and_tag_class_not_null',
                check=(
                    ~Q(
                        state__in=[
                            TaggingBatchState.IMPORTED,
                            TaggingBatchState.IMPORTING,
                            TaggingBatchState.FAILED,
                        ]
                    )
                    | (
                        (Q(tag__isnull=True) & Q(tag_class__isnull=False))
                        | (Q(tag__isnull=False) & Q(tag_class__isnull=True))
                    )
                ),
            )
        ]

    def compute_preflight(
        self, dump_file: Optional[BinaryIO] = None, title_id_formatter: Callable[[int], str] = str
    ) -> dict:
        """
        :param dump_file: opened file where a copy of input will be written with extra data from
                          the processing
        :param title_id_formatter: converter of title id into string
        :return:
        """
        reader = CsvTitleListReader()
        stats = Counter()
        unique_title_ids = set()
        for rec in reader.process_source(
            codecs.iterdecode(self.source_file, 'utf-8'),
            dump_file=dump_file,
            dump_id_formatter=title_id_formatter,
        ):
            stats['row_count'] += 1
            unique_title_ids |= rec.title_ids
            if not rec.title_ids:
                stats['no_match'] += 1
        stats['unique_matched_titles'] = len(unique_title_ids)
        return {
            'stats': stats,
            'explicit_tags': reader.has_explicit_tags,
            'recognized_columns': list(
                sorted(reader.column_names.values(), key=lambda x: x.lower())
            ),
        }

    def do_preflight(self, title_id_formatter: Callable[[int], str] = str):
        """
        :param title_id_formatter: converts title ids to string in the annotated file
        :return:
        """
        try:
            with tempfile.NamedTemporaryFile('r+b') as dump_file:
                self.preflight = self.compute_preflight(
                    dump_file=dump_file, title_id_formatter=title_id_formatter
                )
                self.state = TaggingBatchState.PREFLIGHT
                dump_file.seek(0)
                self.annotated_file = File(dump_file, name=self.create_annotated_file_name())
                self.save()
        except Exception as e:
            self.preflight['error'] = str(e)
            self.state = TaggingBatchState.PREFAILED
            self.save()

    def assign_tag(
        self, create_missing_titles=False, title_id_formatter: Callable[[int], str] = str
    ) -> None:
        """
        :param create_missing_titles: if True, titles which are not found in the database will
                                      be created
        :param title_id_formatter: converts title ids to string in the annotated file
        """
        if self.state != TaggingBatchState.IMPORTING:
            raise ValueError(f'Cannot assign tag for batch in state "{self.state}"')
        if not self.tag.can_user_assign(self.last_updated_by):
            raise PermissionDenied(f'User cannot assing tag #{self.tag_id}')
        reader = CsvTitleListReader()
        stats = Counter()
        unique_title_ids = set()
        unmatched_title_recs = []
        with tempfile.NamedTemporaryFile('wb') as dump_file:
            for rec in reader.process_source(
                codecs.iterdecode(self.source_file, 'utf-8'),
                dump_file=dump_file,
                dump_id_formatter=title_id_formatter,
            ):
                stats['row_count'] += 1
                unique_title_ids |= rec.title_ids
                if not rec.title_ids:
                    stats['no_match'] += 1
                    if create_missing_titles:
                        unmatched_title_recs.append(rec.title_rec)
            dump_file.seek(0)
            with open(dump_file.name, 'rb') as infile:
                if self.annotated_file:
                    # we delete the original annotated_file in order to preserve the original name
                    # and not allow Django to replace it with one with extra junk in the filename
                    self.annotated_file.delete(save=False)
                self.annotated_file = File(infile, name=self.create_annotated_file_name())
                self.save()
        stats['unique_matched_titles'] = len(unique_title_ids)
        if unmatched_title_recs:
            tm = TitleManager()
            tm.prefetch_titles(unmatched_title_recs)
            stats['created_titles'] = -len(unique_title_ids)  # we need the difference after-before
            for title_rec in unmatched_title_recs:
                if title_id := tm.get_or_create(title_rec):
                    unique_title_ids.add(title_id)
            stats['created_titles'] += len(unique_title_ids)

        # do the actual tagging
        to_insert = [
            TitleTag(
                tag_id=self.tag_id,
                target_id=title_id,
                tagging_batch=self,
                _tag_class=self.tag.tag_class,
                _exclusive=self.tag.tag_class.exclusive,
                last_updated_by=self.last_updated_by,
            )
            for title_id in unique_title_ids
        ]
        # because of ignore_conflicts all object from `to_insert` will be returned, even if they
        # were not inserted because of a conflict. This is why we use the actual count of
        # titletags as count of tagged titles
        TitleTag.objects.bulk_create(to_insert, ignore_conflicts=True)
        stats['tagged_titles'] = self.titletag_set.count()
        self.postflight = {'stats': stats}
        self.state = TaggingBatchState.IMPORTED
        self.save()

    def unassign_tag(self) -> None:
        """
        Remove all the TitleTags created by this batch
        """
        if self.state != TaggingBatchState.UNDOING:
            raise ValueError(f'Cannot un-assign tag for batch in state "{self.state}"')
        if not self.tag.can_user_assign(self.last_updated_by):
            raise PermissionDenied(f'User cannot un-assing tag #{self.tag_id}')
        self.titletag_set.all().delete()

    def create_annotated_file_name(self) -> str:
        if not self.source_file:
            raise ValueError('source_file must be filled in')
        _folder, fname = os.path.split(self.source_file.name)
        base, ext = os.path.splitext(fname)
        return base + '-annotated' + ext
