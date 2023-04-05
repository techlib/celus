import pytest
from core.models import DataSource
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from organizations.models import Organization, OrganizationAltName


@pytest.mark.django_db
class TestOrganizationAltName:
    def test_name_uniqueness(self, organizations):
        OrganizationAltName.objects.create(organization=organizations[0], name='foo')
        with pytest.raises(ValidationError):
            # cannot create alt name with the same name and same source
            OrganizationAltName.objects.create(organization=organizations[1], name='foo')

    def test_name_uniqueness_same_source(self, organizations):
        source = DataSource.objects.create(short_name='foo', type=DataSource.TYPE_API)
        OrganizationAltName.objects.create(organization=organizations[0], name='foo', source=source)
        with pytest.raises(ValidationError):
            # cannot create alt name with the same name and same source
            OrganizationAltName.objects.create(
                organization=organizations[1], name='foo', source=source
            )

    def test_name_uniqueness_different_source(self, organizations):
        source = DataSource.objects.create(short_name='foo', type=DataSource.TYPE_API)
        OrganizationAltName.objects.create(organization=organizations[0], name='foo', source=source)
        # can create with a different source - null is implied bellow
        OrganizationAltName.objects.create(organization=organizations[1], name='foo')

    def test_name_uniqueness_with_organization_short_name(self, organizations):

        with pytest.raises(ValidationError):
            OrganizationAltName.objects.create(organization=organizations[0], name='AA')
        with pytest.raises(ValidationError):
            OrganizationAltName.objects.create(organization=organizations[0], name='aa')
        with pytest.raises(ValidationError):
            OrganizationAltName.objects.create(organization=organizations[0], name='aA')

    def test_name_uniqueness_with_organization_name(self, organizations):

        with pytest.raises(ValidationError):
            OrganizationAltName.objects.create(organization=organizations[0], name='AAA')
        with pytest.raises(ValidationError):
            OrganizationAltName.objects.create(organization=organizations[0], name='aaa')
        with pytest.raises(ValidationError):
            OrganizationAltName.objects.create(organization=organizations[0], name='aAa')


@pytest.mark.django_db
class TestOrganization:
    def test_short_name_uniqueness(self, organizations):
        Organization.objects.create(
            ext_id=None,
            parent=None,
            internal_id=None,
            ico=None,
            name_cs='CCC',
            name_en='CCC',
            short_name='CC',
        )
        with pytest.raises(IntegrityError):
            # cannot create name with the same short_name and empty
            Organization.objects.create(
                ext_id=None,
                parent=None,
                internal_id=None,
                ico=None,
                name_cs='DDD',
                name_en='DDD',
                short_name='AA',
            )

    def test_short_name_uniqueness_same_source(self, organizations):
        source = DataSource.objects.create(short_name='foo', type=DataSource.TYPE_API)
        Organization.objects.create(
            ext_id=None,
            parent=None,
            internal_id=None,
            ico=None,
            name_cs='CCC',
            name_en='CCC',
            short_name='CC',
            source=source,
        )
        with pytest.raises(IntegrityError):
            # cannot create name with the same short_name and same source
            Organization.objects.create(
                ext_id=None,
                parent=None,
                internal_id=None,
                ico=None,
                name_cs='DDD',
                name_en='DDD',
                short_name='CC',
                source=source,
            )

    def test_short_name_uniqueness_different_source(self, organizations):
        source = DataSource.objects.create(short_name='foo', type=DataSource.TYPE_API)
        Organization.objects.create(
            ext_id=None,
            parent=None,
            internal_id=None,
            ico=None,
            name_cs='CCC',
            name_en='CCC',
            short_name='CC',
            source=source,
        )
        Organization.objects.create(
            ext_id=None,
            parent=None,
            internal_id='DDD',
            ico=None,
            name_cs='DDD',
            name_en='DDD',
            short_name='CC',
            source=None,
        )
        Organization.objects.create(
            ext_id=None,
            parent=None,
            internal_id=None,
            ico=None,
            name_cs='AAA',
            name_en='AAA',
            short_name='AA',
            source=source,
        )
