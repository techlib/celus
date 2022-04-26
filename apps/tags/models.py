import operator
from functools import reduce
from typing import Optional, Tuple, Type, Union

from colorfield.fields import ColorField
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q, QuerySet
from django.utils.translation import gettext as _
from rest_framework.exceptions import PermissionDenied

from core.models import CreatedUpdatedMixin, REL_ORG_ADMIN, User
from organizations.models import Organization
from publications.models import Platform, Title


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
