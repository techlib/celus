import os
import typing
from hashlib import blake2b
from typing import Optional

from allauth.account.models import EmailAddress, EmailConfirmation
from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.cache import cache
from django.db import models
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django_celery_results.models import TaskResult

from core.exceptions import FileConsistencyError
from core.logic.url import extract_organization_id_from_request_query

UL_NORMAL = 100
UL_ROBOT = 200
UL_ORG_ADMIN = 300
UL_CONS_STAFF = 400
UL_CONS_ADMIN = 1000

USER_LEVEL_CHOICES = (
    (UL_NORMAL, _('Normal user')),
    (UL_ROBOT, _('Robot')),
    (UL_ORG_ADMIN, _('Organization admin')),
    (UL_CONS_STAFF, _('Consortium staff')),
    (UL_CONS_ADMIN, _('Consortium admin')),
)

# relationship between user and accessed resource
REL_SUPERUSER = 1000  # superuser
REL_MASTER_ORG = 400  # user from master organization
REL_ORG_ADMIN = 300  # admin of related organization
REL_ORG_USER = 200  # user from related organization
REL_UNREL_USER = 100  # unrelated user - not from this organization
REL_NO_USER = 0  # no user

# data source types
DATA_SOURCE_TYPE_API = 1
DATA_SOURCE_TYPE_ORGANIZATION = 2
DATA_SOURCE_TYPE_KNOWLEDGEBASE = 3


class DataSource(models.Model):

    """
    Represents a source of data, such as identities, organizations, etc.
    Its main purpose is to be able to distinguish where did different pieces of data come
    from and not to mix user created and ERMS provided data.
    """

    # Keep the source types here as well to keep compatiblity with older versions
    TYPE_API = DATA_SOURCE_TYPE_API
    TYPE_ORGANIZATION = DATA_SOURCE_TYPE_ORGANIZATION
    TYPE_KNOWLEDGEBASE = DATA_SOURCE_TYPE_KNOWLEDGEBASE
    TYPE_CHOICES = (
        (TYPE_API, 'API'),
        (TYPE_ORGANIZATION, 'Organization'),
        (TYPE_KNOWLEDGEBASE, 'Knowledgebase'),
    )

    short_name = models.SlugField()
    type = models.PositiveSmallIntegerField(choices=TYPE_CHOICES)
    url = models.URLField(blank=True)
    token = models.CharField(max_length=64, null=True, blank=True)
    organization = models.OneToOneField(
        'organizations.Organization',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='private_data_source',
        help_text='Used to define data sources private to an organization',
    )

    class Meta:
        constraints = (
            models.CheckConstraint(
                check=(
                    models.Q(type=DATA_SOURCE_TYPE_KNOWLEDGEBASE)
                    & models.Q(token__isnull=False)  # token set
                    & ~models.Q(url__exact="")  # non-empty url
                )
                | ~models.Q(type=DATA_SOURCE_TYPE_KNOWLEDGEBASE),
                name='knowledgebase-requirements',
            ),
            models.UniqueConstraint(
                fields=('url',),
                condition=models.Q(type=DATA_SOURCE_TYPE_KNOWLEDGEBASE),
                name='unique-url-for-knowledgebase',
            ),
            models.UniqueConstraint(
                fields=('short_name',),
                condition=models.Q(type=DATA_SOURCE_TYPE_ORGANIZATION),
                name='source-unique-global-short_name',
            ),
        )

    def __str__(self):
        if self.organization and self.type == self.TYPE_ORGANIZATION:
            return f'Org: {self.organization}'
        return f'{self.short_name}: {self.get_type_display()}'

    @classmethod
    def create_default_short_name(cls, user: 'User', organization_name: str):
        return f"{slugify(user.username)}#{ slugify(organization_name) }"[:50]


class User(AbstractUser):

    EMAIL_VERIFICATION_STATUS_UNKNOWN = "unknown"
    EMAIL_VERIFICATION_STATUS_VERIFIED = "verified"
    EMAIL_VERIFICATION_STATUS_PENDING = "pending"
    EMAIL_VERIFICATION_STATUSES = (
        EMAIL_VERIFICATION_STATUS_UNKNOWN,
        EMAIL_VERIFICATION_STATUS_VERIFIED,
        EMAIL_VERIFICATION_STATUS_PENDING,
    )

    ext_id = models.PositiveIntegerField(
        null=True, blank=True, help_text='ID used in original source of this user data'
    )
    source = models.ForeignKey(DataSource, on_delete=models.SET_NULL, null=True, blank=True)
    language = models.CharField(
        max_length=2,
        choices=settings.AVAILABLE_LANGUAGES,
        default=settings.LANGUAGES[0][0],
        help_text='User\'s preferred language',
    )
    extra_data = models.JSONField(
        default=dict, help_text='User state data that do not deserve a dedicated field', blank=True
    )
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.get_usable_name()

    def get_usable_name(self) -> str:
        if self.first_name or self.last_name:
            return "{0} {1}".format(self.first_name, self.last_name)
        return self.email

    def accessible_organizations(self):
        Organization = apps.get_model(app_label='organizations', model_name='Organization')
        if self.is_superuser or self.is_user_of_master_organization:
            # user is part of one of the master organizations - he should have access to all orgs
            return Organization.objects.all()
        return (
            self.organizations.all()
            | Organization.objects.filter(
                tree_id__in=self.organizations.all().filter(level=0).values('tree_id').distinct()
            )
        ).distinct()
        # the following is an old version where siblings could see each other
        # return Organization.objects.filter(
        #     tree_id__in=self.organizations.all().values('tree_id').distinct())

    def accessible_platforms(
        self, organization: typing.Optional["apps.publications.models.Organization"] = None
    ) -> models.QuerySet:

        """
        Display accessible platform for the user

        :param: organization:
        :returns: queryset with accessible platforms
        """
        Platform = apps.get_model(app_label='publications', model_name='Platform')

        # Platforms with empty source are considered as public
        # + all platforms which belong to the one of user's organization
        query = (
            models.Q(
                source__organization__in=self.accessible_organizations().filter(pk=organization.pk)
            )
            if organization
            else models.Q(source__organization__in=self.accessible_organizations())
        )
        return Platform.objects.filter(~models.Q(source__type=DataSource.TYPE_ORGANIZATION) | query)

    @cached_property
    def is_admin_of_master_organization(self):
        if hasattr(self, 'userorganization_set_prefetched'):
            return any(
                user_org.organization.internal_id in settings.MASTER_ORGANIZATIONS
                and user_org.is_admin
                for user_org in self.userorganization_set_prefetched
            )
        return self.userorganization_set.filter(
            organization__internal_id__in=settings.MASTER_ORGANIZATIONS, is_admin=True
        ).exists()

    @cached_property
    def is_user_of_master_organization(self):
        if hasattr(self, 'userorganization_set_prefetched'):
            return any(
                user_org.organization.internal_id in settings.MASTER_ORGANIZATIONS
                for user_org in self.userorganization_set_prefetched
            )
        return self.organizations.filter(internal_id__in=settings.MASTER_ORGANIZATIONS).exists()

    def request_relationship(self, request):
        """
        Returns the highest ownership level that this user has in relation to request
        :param request:
        :return:
        """
        from organizations.models import Organization, UserOrganization

        if self.is_superuser:
            return REL_SUPERUSER
        elif self.is_admin_of_master_organization:
            return REL_MASTER_ORG
        else:
            org_id = extract_organization_id_from_request_query(request)
            return self.organization_relationship(org_id)

    def organization_relationship(self, org_id: int):
        from organizations.models import Organization, UserOrganization

        if self.is_superuser:
            return REL_SUPERUSER
        elif self.is_admin_of_master_organization:
            return REL_MASTER_ORG
        else:
            if org_id:
                try:
                    # admin must be from the explicitly associated organizations
                    UserOrganization.objects.get(user=self, organization_id=org_id, is_admin=True)
                except UserOrganization.DoesNotExist:
                    try:
                        # user may be from other related organizations
                        self.accessible_organizations().get(pk=org_id)
                    except Organization.DoesNotExist:
                        if self.is_user_of_master_organization:
                            return REL_ORG_USER
                        else:
                            return REL_UNREL_USER
                    else:
                        return REL_ORG_USER
                else:
                    return REL_ORG_ADMIN

            if self.is_user_of_master_organization:
                return REL_ORG_USER
            else:
                return REL_UNREL_USER

    def admin_organizations(self):
        from organizations.models import Organization, UserOrganization

        if self.is_superuser or self.is_admin_of_master_organization:
            # user is part of one of the master organizations - he should have access to all orgs
            return Organization.objects.all()
        return Organization.objects.filter(
            pk__in=UserOrganization.objects.filter(user=self, is_admin=True).values_list(
                'organization_id', flat=True
            )
        )

    def has_organization_admin_permission(self, org_id: int):
        return self.organization_relationship(org_id) >= REL_ORG_ADMIN

    @cached_property
    def email_verification(self) -> dict:
        res = {"status": self.EMAIL_VERIFICATION_STATUS_UNKNOWN, "email_sent": None}
        if settings.ALLOW_EDUID_LOGIN:
            # we consider EduID users as validated and if EduID login is turned on,
            # we consider all users as using EduID.
            res['status'] = self.EMAIL_VERIFICATION_STATUS_VERIFIED
        else:
            try:
                # get current email address from allauth
                email_address: EmailAddress = self.emailaddress_set.get(email__iexact=self.email)
                res["status"] = (
                    self.EMAIL_VERIFICATION_STATUS_VERIFIED
                    if email_address.verified
                    else self.EMAIL_VERIFICATION_STATUS_PENDING
                )
                confirmation: EmailConfirmation = email_address.emailconfirmation_set.last()
                if confirmation:
                    res["email_sent"] = confirmation.sent

            except (EmailAddress.DoesNotExist, EmailConfirmation.DoesNotExist):
                pass
        return res

    @cached_property
    def email_verified(self):
        return self.EMAIL_VERIFICATION_STATUS_VERIFIED == self.email_verification['status']


class Identity(models.Model):

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    identity = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text='External identifier of the person, usually email',
    )
    source = models.ForeignKey(DataSource, on_delete=models.SET_NULL, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'identities'

    def __str__(self):
        return self.identity


class CreatedUpdatedMixin(models.Model):
    created = models.DateTimeField(default=now)
    last_updated = models.DateTimeField(auto_now=True)
    last_updated_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)

    class Meta:
        abstract = True


def where_to_store(instance: models.Model, filename):
    root, ext = os.path.splitext(filename)
    ts = now().strftime('%Y%m%d-%H%M%S.%f')
    # we do not use `isinstance` as it would require importing the models modules which
    # would create circular imports unless we did it locally, which still seems strange.
    if instance.__class__.__name__ == 'SushiFetchAttempt':
        organization = instance.credentials.organization
        return (
            f'counter/{organization.internal_id or organization.pk}/'
            f'{instance.credentials.platform.short_name}/'
            f'{instance.credentials.counter_version}_{instance.counter_report.code}_{ts}{ext}'
        )
    elif instance.__class__.__name__ == 'ManualDataUpload':
        return (
            f'custom/{instance.user_id}/{instance.report_type.short_name}-'
            f'{instance.platform.short_name}_{ts}{ext}'
        )
    else:
        return f'other/{ts}{ext}'


class SourceFileMixin(models.Model):

    DIGEST_SIZE = 32  # byte length of the checksum

    data_file = models.FileField(upload_to=where_to_store, blank=True, null=True, max_length=256)
    checksum = models.CharField(max_length=DIGEST_SIZE * 4)
    file_size = models.PositiveIntegerField()

    class Meta:
        abstract = True

    @classmethod
    def create_hasher(cls):
        return blake2b(digest_size=cls.DIGEST_SIZE)

    @classmethod
    def checksum_fileobj(cls, fileobj) -> (str, int):
        orig_pos = fileobj.tell()
        fileobj.seek(0)
        hasher = cls.create_hasher()
        size = 0
        while chunk := fileobj.read(1024 * 1024):
            if isinstance(chunk, str):
                chunk = chunk.encode('utf-8')
            hasher.update(chunk)
            size += len(chunk)
        fileobj.seek(orig_pos)
        return hasher.hexdigest(), size

    def checksum_self(self) -> (str, int):
        return self.checksum_fileobj(self.data_file)

    def check_fileobj_checksum(self, fileobj):
        """
        Raises exception if the checksum of the file object does not match the stored value
        """
        file_checksum, file_size = self.checksum_fileobj(fileobj)
        if file_checksum != self.checksum:
            self._send_error_mail(fileobj, file_checksum)
            raise FileConsistencyError(
                f'File checksum does not match stored value: '
                f'got "{file_checksum}", expected "{self.checksum}"'
            )

    def check_self_checksum(self):
        self.check_fileobj_checksum(self.data_file)

    def _send_error_mail(self, fileobj, file_checksum):
        """
        Extracted into a separate method to make testing easier
        """
        from core.tasks import async_mail_admins

        async_mail_admins.delay(
            'File checksum mismatch',
            f'File: {getattr(fileobj, "name", "unknown")}\n'
            f'Expected: {self.checksum}\n'
            f'Got: {file_checksum}\n',
        )


class TaskProgress(TaskResult):
    class Meta:
        proxy = True

    @property
    def cache_key_total(self) -> str:
        return f'{self.task_id}-total'

    @property
    def cache_key_current(self) -> str:
        return f'{self.task_id}-current'

    @property
    def progress_current(self) -> Optional[int]:
        return cache.get(self.cache_key_current)

    @property
    def progress_total(self) -> Optional[int]:
        return cache.get(self.cache_key_total)

    def store_progress(self, current: Optional[int], total: Optional[int]):
        cache.set(self.cache_key_current, current)
        cache.set(self.cache_key_total, total)
