import logging
import operator
import os
import tempfile
from collections import Counter, defaultdict
from functools import reduce
from typing import BinaryIO, Callable, Dict, Iterable, List, Optional, Tuple, Type, Union

import magic
from colorfield.fields import ColorField
from core.models import REL_ORG_ADMIN, CreatedUpdatedMixin, User
from django.conf import settings
from django.core.files.base import File
from django.db import models
from django.db.models import Count, Exists, OuterRef, Prefetch, Q, QuerySet, Subquery, Value
from django.db.transaction import atomic
from django.utils.timezone import now
from django.utils.translation import gettext as _
from organizations.models import Organization
from publications.models import Platform, Title
from rest_framework.exceptions import PermissionDenied, ValidationError

from tags.logic.titles_lists import CsvTitleListReader, TitleListReader

logger = logging.getLogger(__name__)


class AccessibleBy(models.IntegerChoices):
    EVERYBODY = 10, _("Everybody")
    ORG_USERS = 20, _("Organization users")
    ORG_ADMINS = 30, _("Organization admins")
    CONS_ADMINS = 40, _("Consortium admins")
    OWNER = 50, _("Owner")
    SYSTEM = 100, _("System")  # only internal Celus functions can access this

    @classmethod
    def org_related(cls) -> Tuple["AccessibleBy", "AccessibleBy"]:
        return (cls.ORG_USERS, cls.ORG_ADMINS)


class TagScope(models.TextChoices):
    TITLE = "title", _("Title")
    PLATFORM = "platform", _("Platform")
    ORGANIZATION = "organization", _("Organization")


class TaggingAttemptOperation(models.TextChoices):
    PREFLIGHT = "preflight", _("Preflight")
    IMPORT = "import", _("Import")


def access_filters(attr_name: str, user: User) -> Q:
    """
    Returns a filter for queryset which applies relevant checks on the `attr_name` attribute
    which is a choice of type `AccessibleBy`
    """
    possibilities = [
        Q(**{attr_name: AccessibleBy.EVERYBODY}),
        Q(**{attr_name: AccessibleBy.OWNER, "owner": user}),
        Q(**{attr_name: AccessibleBy.ORG_USERS, "owner_org__in": user.accessible_organizations()}),
        Q(**{attr_name: AccessibleBy.ORG_ADMINS, "owner_org__in": user.admin_organizations()}),
    ]
    if user.is_superuser or user.is_admin_of_master_organization:
        possibilities.append(Q(**{attr_name: AccessibleBy.CONS_ADMINS}))

    return reduce(operator.or_, possibilities)


class TagClassQuerySet(models.QuerySet):
    def user_accessible_tag_classes(self, user: User) -> QuerySet["TagClass"]:
        """
        These are the tag classes to which the user can add tags
        """
        return self.filter(access_filters("can_create_tags", user))

    def user_modifiable_tag_classes(self, user: User) -> QuerySet["TagClass"]:
        return self.filter(access_filters("can_modify", user))

    def user_assignable_tag_classes(self, user: User) -> QuerySet["TagClass"]:
        """
        These are the tag classes to which the user can add tags
        """
        return self.filter(access_filters("default_tag_can_assign", user))

    def with_user_visible_tags(self, user: User) -> QuerySet["TagClass"]:
        in_visible_tags = Tag.objects.user_accessible_tags(user).values("tag_class_id").distinct()
        return self.filter(Q(id__in=in_visible_tags))

    def annotate_hidden(self, user: User) -> QuerySet["TagClass"]:
        """
        Annotates the queryset with a boolean field `hidden` which is True if the user has
        marked the tag class as hidden
        """
        return self.annotate(
            hidden=Exists(
                UserTagClass.objects.filter(
                    user=user, tag_class_id=models.OuterRef("id"), hidden=True
                )
            )
        )

    def annotate_user_score(self, user: User) -> QuerySet["TagClass"]:
        """
        Adds a numeric score from the `AccessibleBy` scale to each tag class. The score is
        based on the relationship the user has to the tag class.
        """
        return self.annotate(
            user_score=models.Case(
                models.When(owner=user, then=models.Value(AccessibleBy.OWNER)),
                models.When(
                    models.Value(user.is_superuser or user.is_admin_of_master_organization),
                    then=models.Value(AccessibleBy.CONS_ADMINS),
                ),
                models.When(
                    owner_org__in=user.admin_organizations(),
                    then=models.Value(AccessibleBy.ORG_ADMINS),
                ),
                models.When(
                    owner_org__in=user.accessible_organizations(),
                    then=models.Value(AccessibleBy.ORG_USERS),
                ),
                default=models.Value(AccessibleBy.EVERYBODY),
            )
        )


class TagClass(CreatedUpdatedMixin, models.Model):
    internal = models.BooleanField(default=False)
    scope = models.CharField(max_length=16, choices=TagScope.choices)
    name = models.CharField(max_length=200)
    exclusive = models.BooleanField(
        default=False, help_text="An item may be only tagged by one tag from an exclusive tag class"
    )
    text_color = ColorField(default="#303030")
    bg_color = ColorField(default="#E2E2E2")
    desc = models.CharField(max_length=160, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.CASCADE,
        blank=True,
        help_text='When an access level is set to "owner", this specifies the one',
        related_name="owned_tagclasses",
    )
    owner_org = models.ForeignKey(
        Organization,
        null=True,
        on_delete=models.CASCADE,
        blank=True,
        help_text='When an access level is set to "organization users" or "organization admin", '
        "this is the organization",
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
        ordering = ["name"]
        verbose_name_plural = "Tag classes"
        constraints = [
            models.CheckConstraint(
                # owner must be set if can_modify or can_create_tags is set to OWNER
                name="tag_class_owner_not_null",
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
                name="tag_class_owner_org_not_null",
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
    def tag_scope_from_target_class(
        cls, target_class: Union[Type[Platform], Type[Title], Type[Organization]]
    ) -> TagScope:
        if target_class is Title:
            return TagScope.TITLE
        elif target_class is Platform:
            return TagScope.PLATFORM
        elif target_class is Organization:
            return TagScope.ORGANIZATION
        raise ValueError(f'Unexpected target class "{target_class}"')

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

    def change_hidden_for_user(self, user: User, hidden: bool):
        UserTagClass.objects.update_or_create(
            user=user, tag_class=self, defaults={"hidden": hidden}
        )

    def get_or_create_tags(self, tag_names: Iterable[str], owner: User) -> Dict[str, "Tag"]:
        """
        Returns a dictionary of tags with keys being the tag names. If a tag with the name
        already exists, it is returned, otherwise it is created.
        """
        out = {tag.name: tag for tag in Tag.objects.filter(tag_class=self, name__in=tag_names)}
        missing_names = set(tag_names) - set(out.keys())
        to_insert = [
            Tag(
                tag_class=self,
                name=name,
                owner=owner,
                can_assign=self.default_tag_can_assign,
                can_see=self.default_tag_can_see,
            )
            for name in missing_names
        ]
        if to_insert:
            inserted = Tag.objects.bulk_create(to_insert)
            out.update({tag.name: tag for tag in inserted})
        return out


class TagQuerySet(models.QuerySet):
    def user_accessible_tags(self, user: User) -> QuerySet["Tag"]:
        return self.filter(access_filters("can_see", user))

    def user_assignable_tags(self, user: User) -> QuerySet["Tag"]:
        return self.filter(access_filters("can_assign", user))

    def user_modifiable_tags(self, user: User) -> QuerySet["Tag"]:
        return self.filter(tag_class__in=TagClass.objects.user_accessible_tag_classes(user))


class Tag(CreatedUpdatedMixin, models.Model):
    tag_class = models.ForeignKey(TagClass, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    text_color = ColorField(default="#303030")
    bg_color = ColorField(default="#E2E2E2")
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
        related_name="owned_tags",
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
    titles = models.ManyToManyField(Title, through="TitleTag", related_name="tags")
    platforms = models.ManyToManyField(Platform, through="PlatformTag", related_name="tags")
    organizations = models.ManyToManyField(
        Organization, through="OrganizationTag", related_name="tags"
    )

    # custom manager
    objects = TagQuerySet.as_manager()

    class Meta:
        ordering = ["name"]
        verbose_name = _("Tag")
        constraints = [
            models.CheckConstraint(
                # owner must be set if can_see or can_assign is set to OWNER
                name="tag_owner_not_null",
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
                name="tag_owner_org_not_null",
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

    @property
    def full_name(self):
        return f"{self.tag_class.name} / {self.name}"

    @classmethod
    def link_class_from_target(
        cls, target: Union[Title, Platform, Organization]
    ) -> Type["ItemTag"]:
        if isinstance(target, Title):
            return TitleTag
        elif isinstance(target, Platform):
            return PlatformTag
        elif isinstance(target, Organization):
            return OrganizationTag
        raise ValueError(f'unsupported target object of class "{target.__class__}"')

    @classmethod
    def link_class_from_scope(cls, scope: TagScope) -> Type["ItemTag"]:
        if scope == TagScope.TITLE:
            return TitleTag
        elif scope == TagScope.PLATFORM:
            return PlatformTag
        elif scope == TagScope.ORGANIZATION:
            return OrganizationTag
        raise ValueError(f'unsupported scope "{scope}"')

    @classmethod
    def target_attr_from_scope(cls, scope: TagScope) -> str:
        if scope == TagScope.TITLE:
            return "titles"
        elif scope == TagScope.PLATFORM:
            return "platforms"
        elif scope == TagScope.ORGANIZATION:
            return "organizations"
        raise ValueError(f'unsupported scope "{scope}"')

    def tag(self, target: Union[Title, Platform, Organization], user: User) -> "ItemTag":
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
    ) -> "ItemTag":
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

    def can_user_modify(self, user: User) -> bool:
        return Tag.objects.user_modifiable_tags(user).filter(pk=self.pk).exists()


class ItemTag(CreatedUpdatedMixin, models.Model):
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    target = models.ForeignKey(Title, on_delete=models.CASCADE)  # just to have something here
    tagging_batch = models.ForeignKey(
        "TaggingBatch",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="If the tagging was done in a batch, this is the batch",
    )
    tagging_attempt = models.ForeignKey(
        "TaggingAttempt",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="If the tagging was done in a batch, this is the specific attempt",
        limit_choices_to=Q(operation=TaggingAttemptOperation.IMPORT),
    )
    # the following is redundant, but we need it for a constraint
    _tag_class = models.ForeignKey(TagClass, on_delete=models.CASCADE)
    _exclusive = models.BooleanField()

    class Meta:
        abstract = True
        unique_together = [("tag", "target")]
        constraints = [
            models.UniqueConstraint(
                fields=("target", "_tag_class"),
                condition=Q(_exclusive=True),
                name="%(class)s_unique_tag_class_for_exclusive",
            ),
        ]

    def save(self, **kwargs):
        self._tag_class_id = self.tag.tag_class_id
        self._exclusive = self.tag.tag_class.exclusive
        super().save(**kwargs)

    @classmethod
    def get_subclass_by_item_type(cls, item_type: TagScope) -> Type["ItemTag"]:
        if item_type == TagScope.TITLE:
            return TitleTag
        elif item_type == TagScope.PLATFORM:
            return PlatformTag
        elif item_type == TagScope.ORGANIZATION:
            return OrganizationTag
        raise ValueError(f'Unexpected item type "{item_type}"')


class TitleTag(ItemTag):
    target = models.ForeignKey(Title, on_delete=models.CASCADE)


class PlatformTag(ItemTag):
    target = models.ForeignKey(Platform, on_delete=models.CASCADE)


class OrganizationTag(ItemTag):
    target = models.ForeignKey(Organization, on_delete=models.CASCADE)


def where_to_store(instance: "TaggingBatch", filename):
    root, ext = os.path.splitext(filename)
    ts = now().strftime("%Y%m%d-%H%M%S.%f")
    return f"tagging_batch/{root}-{ts}{ext}"


class TaggingBatchState(models.TextChoices):
    """
    I originally used `MduState` for this, but needed the `UNDOING` state for the unassigning
    process. Because inheritance is not possible, I had to recreate the whole thing, but kept the
    original names so that I do not have to change the frontend code.
    """

    INITIAL = "initial", _("Initial")
    PREPROCESSING = "preprocessing", _("Preprocessing")
    PREFLIGHT = "preflight", _("Preflight")
    IMPORTING = "importing", _("Importing")
    IMPORTED = "imported", _("Imported")
    PREFAILED = "prefailed", _("Preflight failed")
    FAILED = "failed", _("Import failed")
    UNDOING = "undoing", _("Undoing")


def validate_mime_type(fileobj):
    pos = fileobj.tell()
    fileobj.seek(0)
    try:
        detected_type = magic.from_buffer(fileobj.read(16384), mime=True)
    finally:
        fileobj.seek(pos)
    # there is no one type to rule them all - magic is not perfect and we need to consider
    # other possibilities that could be detected - for example the text/x-Algol68 seems
    # to be returned for some CSV files with some version of libmagic
    # (the library magic uses internally)
    if detected_type not in ("text/csv", "text/plain", "application/csv", "text/x-Algol68"):
        raise ValidationError(
            _(
                "The uploaded file does not seem to be a CSV file. "
                "The file type seems to be '{detected_type}'. "
                "Please upload a CSV file."
            ).format(detected_type=detected_type)
        )


class TaggingBatchQuerySet(models.QuerySet):
    def prefetch_attempts(self) -> QuerySet:
        """
        Annotates the queryset with the last preflight and import attempts
        """
        return self.prefetch_related(
            Prefetch(
                "taggingattempts",
                to_attr="_last_preflights",
                queryset=TaggingAttempt.objects.filter(
                    operation=TaggingAttemptOperation.PREFLIGHT
                ).order_by("-created"),
            ),
            Prefetch(
                "taggingattempts",
                to_attr="_last_imports",
                queryset=TaggingAttempt.objects.filter(
                    operation=TaggingAttemptOperation.IMPORT
                ).order_by("-created"),
            ),
        )

    def annotate_import_count(self) -> QuerySet["TaggingBatch"]:
        """
        Annotates the queryset with the number of imported tags
        """
        # we do not use simple Count annotation because it would then do GROUP BY id
        # on the query and this could then interfere with other queries which do locking, etc.
        # which is not compatible with GROUP BY
        return self.annotate(
            import_count=Subquery(
                TaggingAttempt.objects.filter(
                    batch=OuterRef("id"),
                    operation=TaggingAttemptOperation.IMPORT,
                )
                .order_by()
                .annotate(x=Value(7))  # to ensure all sub-rows have the same value
                .values("x")
                .annotate(c=Count("id"))  # aggregating all sub-rows into one value
                .values("c")
            )
        )

    def to_reprocess(self) -> QuerySet["TaggingBatch"]:
        """
        Returns the batches which should be reprocessed
        """
        return self.filter(
            state=TaggingBatchState.IMPORTED,
            reprocess_after__isnull=False,
        ).exclude(
            Exists(  # check if recent import exists
                TaggingAttempt.objects.filter(
                    batch=OuterRef("pk"),
                    operation=TaggingAttemptOperation.IMPORT,
                    last_updated__gt=now() - OuterRef("reprocess_after"),
                )
            )
        )


class TaggingBatch(CreatedUpdatedMixin, models.Model):
    TAG_COLUMN_NAME = "tag"

    source_file = models.FileField(
        upload_to=where_to_store,
        blank=True,
        null=True,
        max_length=256,
        validators=[validate_mime_type],
    )
    annotated_file = models.FileField(
        upload_to="tagging_batch/",
        blank=True,
        null=True,
        max_length=256,
        help_text="File with additional data added during pre-flight or import",
    )
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, blank=True, null=True)
    tag_class = models.ForeignKey(TagClass, on_delete=models.CASCADE, blank=True, null=True)
    state = models.CharField(
        max_length=20, choices=TaggingBatchState.choices, default=TaggingBatchState.INITIAL
    )
    internal_name = models.CharField(
        max_length=64,
        blank=True,
        help_text="When given, it marks the batch as internal. Such batches are not shown in the "
        "UI. It also serves as identification of such batches internally.",
    )
    reprocess_after = models.DurationField(
        null=True,
        blank=True,
        help_text="When not null, it specifies the interval after which the tagging batch will be "
        "re-imported (new attempt will be created).",
    )

    objects = TaggingBatchQuerySet.as_manager()

    class Meta:
        verbose_name_plural = "Tagging batches"
        constraints = [
            models.CheckConstraint(
                # either tag or tag_class must be set, but not both, if the state is
                # imported, importing or failed
                # in other cases, we do not care about tag or tag_class
                name="one_of_tag_and_tag_class_not_null",
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
            ),
            models.UniqueConstraint(
                fields=["internal_name"],
                condition=~Q(internal_name=""),
                name="internal_name_unique",
            ),
        ]

    @property
    def needs_tag_column(self) -> bool:
        """
        Returns true if `tag_class` is set, but `tag` is not. This means that the info about
        tags should be in the source file.
        """
        return bool(not self.tag and self.tag_class)

    @property
    def file_columns(self) -> List[str]:
        """
        Returns list of column names of the source file.
        """
        orig_pos = self.source_file.tell()
        self.source_file.seek(0)
        columns = CsvTitleListReader().fieldnames(self.source_file)
        self.source_file.seek(orig_pos)
        return columns

    @property
    def preflights(self):
        return self.taggingattempts.filter(operation=TaggingAttemptOperation.PREFLIGHT).order_by(
            "created"
        )

    @property
    def imports(self):
        return self.taggingattempts.filter(operation=TaggingAttemptOperation.IMPORT).order_by(
            "created"
        )

    @property
    def misses_tag_column(self) -> bool:
        """
        Returns true if the source file does not contain the column with the tag.
        """
        if not self.needs_tag_column:
            return False
        return not any(c.lower().strip() == self.TAG_COLUMN_NAME for c in self.file_columns)

    @property
    def last_preflight(self) -> Optional["TaggingAttempt"]:
        """
        Returns the last preflight attempt
        """
        if hasattr(self, "_last_preflights"):
            # we have the preflights already prefetched
            return self._last_preflights[0] if self._last_preflights else None
        return self.preflights.last()

    @property
    def last_import(self) -> Optional["TaggingAttempt"]:
        """
        Returns the last import attempt
        """
        if hasattr(self, "_last_imports"):
            # we have the imports already prefetched
            return self._last_imports[0] if self._last_imports else None
        return self.imports.last()

    def file_row_count(self):
        orig_pos = self.source_file.tell()
        self.source_file.seek(0)
        total = CsvTitleListReader().record_count(self.source_file)
        self.source_file.seek(orig_pos)
        return total

    def get_used_tags(self) -> Optional[QuerySet["Tag"]]:
        """
        Returns a queryset of tags which are used in this batch - only makes sense after
        tagging was finished
        """
        if self.state not in [TaggingBatchState.IMPORTED, TaggingBatchState.UNDOING]:
            return None
        if self.tag:
            return Tag.objects.filter(pk=self.tag.pk)
        elif self.tag_class:
            tag_ids = set(self.titletag_set.distinct("tag_id").values_list("tag_id", flat=True))
            return Tag.objects.filter(pk__in=tag_ids)
        else:
            raise ValueError("We should never get here in imported state")

    def compute_preflight(
        self,
        dump_file: Optional[BinaryIO] = None,
        title_id_formatter: Callable[[int], str] = str,
        progress_monitor: Optional[Callable[[int, int], None]] = None,
    ) -> "TaggingAttempt":
        """
        :param dump_file: opened file where a copy of input will be written with extra data from
                          the processing
        :param title_id_formatter: converter of title id into string
        :param progress_monitor: callback to report progress, should send (current, total) ints
        :return:
        """
        self._check_prerequisites()
        reader = CsvTitleListReader(
            tag_name_column=self.TAG_COLUMN_NAME if self.needs_tag_column else None,
            dump_id_formatter=title_id_formatter,
        )
        stats = Counter()
        unique_title_ids = set()
        total = self.file_row_count()
        tag_to_matched_lines = Counter()
        tag_to_unique_title_ids = defaultdict(set)
        for rec in reader.process_source(self.source_file, dump_file=dump_file):
            stats["row_count"] += 1
            unique_title_ids |= rec.title_ids
            if not rec.title_ids:
                stats["no_match"] += 1
            if progress_monitor:
                progress_monitor(stats["row_count"], total)
            if self.needs_tag_column:
                # stats related to explicit tags in file
                tags = {name for name in rec.tag_names}
                if not tags:
                    stats["rows_no_tag"] += 1
                else:
                    for tag in tags:
                        tag_to_matched_lines[tag] += 1
                        if rec.title_ids:
                            tag_to_unique_title_ids[tag] |= rec.title_ids

        tag_stats = {}
        if self.needs_tag_column:
            tag_stats = {
                key: {
                    "matched_lines": value,
                    "matched_titles": len(tag_to_unique_title_ids[key]),
                }
                for key, value in tag_to_matched_lines.items()
            }
        return TaggingAttempt(
            batch=self,
            operation=TaggingAttemptOperation.PREFLIGHT,
            recognized_columns=sorted(reader.column_names.values(), key=lambda x: x.lower()),
            rows_total=stats["row_count"],
            rows_no_match=stats["no_match"],
            rows_no_tag=stats["rows_no_tag"],
            unique_matched_titles=len(unique_title_ids),
            tag_stats=tag_stats,
        )

    def _check_prerequisites(self):
        if not self.tag and not self.tag_class:
            raise ValueError("Either tag or tag_class must be set")
        if self.misses_tag_column:
            raise ValueError("The source file does not contain the `tag` column")

    def do_preflight(
        self,
        title_id_formatter: Callable[[int], str] = str,
        progress_monitor: Optional[Callable[[int, int], None]] = None,
    ) -> "TaggingAttempt":
        """
        :param title_id_formatter: converts title ids to string in the annotated file
        :param progress_monitor: callback to report progress, should send (current, total) ints
        :return:
        """
        try:
            with tempfile.NamedTemporaryFile("r+b") as dump_file:
                preflight = self.compute_preflight(
                    dump_file=dump_file,
                    title_id_formatter=title_id_formatter,
                    progress_monitor=progress_monitor,
                )
                self.state = TaggingBatchState.PREFLIGHT
                dump_file.seek(0)
                self.annotated_file = File(dump_file, name=self.create_annotated_file_name())
                preflight.save()
                self.save()
        except Exception as e:
            logger.error("Error during preflight", exc_info=True)
            preflight = TaggingAttempt.objects.create(
                batch=self, operation=TaggingAttemptOperation.PREFLIGHT, success=False, error=str(e)
            )
            self.state = TaggingBatchState.PREFAILED
            self.save()
        if hasattr(self, "_last_preflights"):
            # we have the preflights already prefetched and need to update them
            self._last_preflights.insert(0, preflight)
        return preflight

    @atomic
    def assign_tag(
        self,
        title_id_formatter: Callable[[int], str] = str,
        progress_monitor: Optional[Callable[[int, int], None]] = None,
        system_process: bool = False,
    ) -> "TaggingAttempt":
        """
        :param title_id_formatter: converts title ids to string in the annotated file
        :param progress_monitor: callback to report progress, should send (current, total) ints
        :param system_process: if True, the tag is assigned by the system and the user is not
        checked
        """
        try:
            self._check_prerequisites()
            self._preassign_checks(system_process=system_process)
            postflight = self._do_assign_tag(title_id_formatter, progress_monitor)
        except Exception as e:
            logger.error("Error during tagging", exc_info=True)
            postflight = TaggingAttempt.objects.create(
                batch=self, operation=TaggingAttemptOperation.IMPORT, success=False, error=str(e)
            )
            self.state = TaggingBatchState.FAILED
        else:
            # update batch
            self.state = TaggingBatchState.IMPORTED
        self.save()
        if hasattr(self, "_last_imports"):
            # we have the imports already prefetched and need to update them
            self._last_imports.insert(0, postflight)
        return postflight

    def _preassign_checks(self, system_process: bool = False):
        """
        Checks that the batch is in the correct state and that the user can assign the tag.
        If `system_process` is True, the user is not checked.
        """
        if self.state != TaggingBatchState.IMPORTING:
            raise ValueError(f'Cannot assign tag for batch in state "{self.state}"')
        if system_process:
            return
        if self.tag and not self.tag.can_user_assign(self.last_updated_by):
            raise PermissionDenied(f"User cannot assign tag #{self.tag_id}")
        if self.tag_class and self.tag_class not in TagClass.objects.user_accessible_tag_classes(
            self.last_updated_by
        ):
            raise PermissionDenied(f"User cannot add tags to class #{self.tag_class}")

    def _do_assign_tag(
        self,
        title_id_formatter: Callable[[int], str] = str,
        progress_monitor: Optional[Callable[[int, int], None]] = None,
    ):
        rows_total = self.file_row_count()
        reader = CsvTitleListReader(
            dump_id_formatter=title_id_formatter,
            tag_name_column=self.TAG_COLUMN_NAME if self.needs_tag_column else None,
        )
        stats = Counter()

        tag_to_matched_lines, tag_to_unique_title_ids = self._process_file_for_assignment(
            reader, rows_total, stats, progress_monitor
        )
        # do the actual tagging
        # postflight (import) is referenced in TitleTag, so we need to create it first
        postflight = TaggingAttempt.objects.create(
            batch=self, operation=TaggingAttemptOperation.IMPORT
        )
        to_insert = []
        if self.tag:
            tag_name_to_tag = {None: self.tag}
            tc = self.tag.tag_class
        else:
            tag_name_to_tag = self.tag_class.get_or_create_tags(
                tag_to_unique_title_ids.keys(), self.last_updated_by
            )
            tc = self.tag_class
        for tag_name, title_ids in tag_to_unique_title_ids.items():
            tag = tag_name_to_tag[tag_name]
            to_insert += [
                TitleTag(
                    tag_id=tag.pk,
                    target_id=title_id,
                    tagging_batch=self,
                    tagging_attempt=postflight,
                    _tag_class=tc,
                    _exclusive=tc.exclusive,
                    last_updated_by=self.last_updated_by,
                )
                for title_id in title_ids
            ]
        if progress_monitor:
            # report another part of the progress
            progress_monitor(2 * stats["row_count"] // 3, rows_total)
        # because of ignore_conflicts all object from `to_insert` will be returned, even if they
        # were not inserted because of a conflict. This is why we use the actual count of
        # titletags as count of tagged titles
        TitleTag.objects.bulk_create(to_insert, ignore_conflicts=True)
        # postflight is connected only to currently tagged items (self is to all)
        tagged_titles_count = postflight.titletag_set.values("target_id").distinct().count()
        # compute unique titles matched for all tags
        unique_title_ids = reduce(operator.or_, tag_to_unique_title_ids.values(), set())
        # we want to count what was already tagged before and what is tagged with a different
        # exclusive tag
        if tc.exclusive:
            qs = TitleTag.objects.filter(tag__tag_class=tc, target_id__in=unique_title_ids).exclude(
                tagging_attempt=postflight
            )
            if self.tag:
                # if we are tagging with a single tag, we need to exclude it from the count
                # because it should fall to the `already_tagged_titles` count which is computed
                # later
                qs = qs.exclude(tag=self.tag)
            exclusively_tagged_titles_count = qs.count()
        else:
            exclusively_tagged_titles_count = 0
        # if it is not exclusively tagged and was not tagged, it must have been tagged before
        unique_matched_titles = len(unique_title_ids)
        already_tagged_titles = (
            unique_matched_titles - tagged_titles_count - exclusively_tagged_titles_count
        )
        if progress_monitor:
            # report the rest of the progress
            progress_monitor(stats["row_count"], rows_total)
        # update postflight
        postflight.rows_total = stats["row_count"]
        postflight.rows_no_match = stats["no_match"]
        postflight.unique_matched_titles = unique_matched_titles
        postflight.already_tagged_titles = already_tagged_titles
        postflight.tagged_titles = tagged_titles_count
        postflight.exclusively_tagged_titles = exclusively_tagged_titles_count
        postflight.recognized_columns = sorted(
            reader.column_names.values(), key=lambda x: x.lower()
        )
        # tag statistics
        tag_stats = {}
        if self.needs_tag_column:
            tag_usage = {
                rec["tag__name"]: rec["c"]
                for rec in postflight.titletag_set.values("tag__name").annotate(
                    c=Count("target_id")
                )
            }
            tag_stats = {
                key: {
                    "matched_lines": value,
                    "matched_titles": len(tag_to_unique_title_ids[key]),
                    "tagged_titles": tag_usage.get(key, 0),
                }
                for key, value in tag_to_matched_lines.items()
            }
        postflight.tag_stats = tag_stats
        postflight.save()
        return postflight

    def _process_file_for_assignment(
        self,
        reader: TitleListReader,
        rows_total: int,
        stats: Counter,
        progress_monitor: Optional[Callable[[int, int], None]] = None,
    ):
        """
        Internal function to process the file and return the stats and the mapping of tag names
        """
        tag_to_unique_title_ids = defaultdict(set)
        tag_to_matched_lines = Counter()
        with tempfile.NamedTemporaryFile("wb") as dump_file:
            for rec in reader.process_source(self.source_file, dump_file=dump_file):
                stats["row_count"] += 1
                tag_names = [None] if self.tag else rec.tag_names
                if not rec.title_ids:
                    stats["no_match"] += 1
                else:
                    for tag_name in tag_names:
                        tag_to_unique_title_ids[tag_name] |= rec.title_ids
                if self.needs_tag_column:
                    for tag_name in rec.tag_names:
                        tag_to_matched_lines[tag_name] += 1
                if progress_monitor:
                    # report only half of the progress, because we are doing the insertion into
                    # the database later
                    progress_monitor(stats["row_count"] // 2, rows_total)
            dump_file.seek(0)
            with open(dump_file.name, "rb") as infile:
                if self.annotated_file:
                    # we delete the original annotated_file in order to preserve the original name
                    # and not allow Django to replace it with one with extra junk in the filename
                    self.annotated_file.delete(save=False)
                self.annotated_file = File(infile, name=self.create_annotated_file_name())
                self.save()
        return tag_to_matched_lines, tag_to_unique_title_ids

    def unassign_tag(self, progress_monitor: Optional[Callable[[int, int], None]] = None) -> None:
        """
        Remove all the TitleTags created by this batch
        :param progress_monitor: callback to report progress, should send (current, total) ints
        """
        if self.state != TaggingBatchState.UNDOING:
            raise ValueError(f'Cannot un-assign tag for batch in state "{self.state}"')
        if self.tag and not self.tag.can_user_assign(self.last_updated_by):
            raise PermissionDenied(f"User cannot (un)assing tag #{self.tag_id}")
        elif self.tag_class:
            # we need to get all the tags for this batch and check all of them
            used_tags = self.get_used_tags()
            used_tags_count = used_tags.count()
            if used_tags.user_assignable_tags(self.last_updated_by).count() < used_tags_count:
                raise PermissionDenied("User cannot (un)assing some tags assigned in this batch")
        # we report progress just to be compatible with the other operations, but the way
        # we do it, the operation is almost immediate
        rows_total = self.titletag_set.count()
        if progress_monitor:
            # report start
            progress_monitor(0, rows_total)
        self.titletag_set.all().delete()
        self.taggingattempts.all().delete()
        if progress_monitor:
            progress_monitor(rows_total, rows_total)

    def create_annotated_file_name(self) -> str:
        if not self.source_file:
            raise ValueError("source_file must be filled in")
        _folder, fname = os.path.split(self.source_file.name)
        base, ext = os.path.splitext(fname)
        return base + "-annotated" + ext


class TaggingAttempt(CreatedUpdatedMixin, models.Model):
    """
    Represents one attempt to process a tagging batch. It can represent either a preflight
    or actual tagging operation.
    Each `TaggingBatch` may have a number of `TaggingAttempt`s because both preflight and import
    may be repreated multiple times (after new titles were added to the database, etc.)
    """

    batch = models.ForeignKey(
        TaggingBatch, on_delete=models.CASCADE, related_name="taggingattempts"
    )
    operation = models.CharField(choices=TaggingAttemptOperation.choices, max_length=10)
    success = models.BooleanField(
        default=True,
        help_text="Whether the operation was successful. If not `error` should have more info",
    )
    error = models.TextField(
        blank=True, help_text="In case of failure contains info about the error"
    )
    # stats
    recognized_columns = models.JSONField(default=list, help_text="List of column names")
    tag_stats = models.JSONField(
        default=dict, help_text="Dict with tags as keys and dicts with different counts as values"
    )
    rows_total = models.PositiveIntegerField(
        default=0, help_text="Total number of rows in the source file"
    )
    rows_no_match = models.PositiveIntegerField(default=0, help_text="Rows with no matched title")
    rows_no_tag = models.PositiveIntegerField(default=0, help_text="Rows with no tag information")
    unique_matched_titles = models.PositiveIntegerField(
        default=0, help_text="Number of unique matched titles"
    )
    already_tagged_titles = models.PositiveIntegerField(
        default=0,
        help_text="Titles already tagged with the tag(s) as hand - these will not be tagged again",
    )
    tagged_titles = models.PositiveIntegerField(
        default=0, help_text="In preflight means 'to be tagged'"
    )
    # the following are only for import
    exclusively_tagged_titles = models.PositiveIntegerField(
        default=0,
        help_text="Number of titles which were already tagged with another tag from a mutually "
        "exclusive tag class and thus were not tagged with the tag(s) as hand",
    )

    class Meta:
        ordering = ("batch_id", "created")


class UserTagClass(models.Model):
    """
    Intermediate model for many-to-many relationship between User and TagClass.
    Currently only serves to store `hidden` flag.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tag_class = models.ForeignKey(TagClass, on_delete=models.CASCADE)
    hidden = models.BooleanField(default=True)
    created = models.DateTimeField(default=now)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "tag_class")
