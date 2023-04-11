import pytest
from core.models import DataSource
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from organizations.models import Organization, OrganizationAltName

from test_fixtures.entities.organizations import OrganizationAltNameFactory, OrganizationFactory


@pytest.mark.django_db
class TestOrganizationAltName:
    def test_name_uniqueness(self, organizations):
        OrganizationAltNameFactory(organization=organizations[0], name='foo')
        with pytest.raises(ValidationError):
            # cannot create alt name with the same name and same source
            OrganizationAltName.objects.create(organization=organizations[1], name='foo')

    def test_name_uniqueness_same_source(self, organizations):
        source = DataSource.objects.create(short_name='foo', type=DataSource.TYPE_API)
        OrganizationAltNameFactory(organization=organizations[0], name='foo', source=source)
        with pytest.raises(ValidationError):
            # cannot create alt name with the same name and same source
            OrganizationAltName.objects.create(
                organization=organizations[1], name='foo', source=source
            )

    def test_name_uniqueness_different_source(self, organizations):
        source = DataSource.objects.create(short_name='foo', type=DataSource.TYPE_API)
        OrganizationAltNameFactory(organization=organizations[0], name='foo', source=source)
        # can create with a different source - null is implied bellow
        OrganizationAltNameFactory(organization=organizations[1], name='foo')

    def test_name_uniqueness_with_organization_short_name(self):
        organization = OrganizationFactory(
            internal_id='AAA',
            name_cs='AAA',
            name_en='AAA',
            short_name='AA',
        )

        with pytest.raises(ValidationError):
            OrganizationAltNameFactory(organization=organization, name='AA')
        with pytest.raises(ValidationError):
            OrganizationAltNameFactory(organization=organization, name='aa')
        with pytest.raises(ValidationError):
            OrganizationAltNameFactory(organization=organization, name='aA')

    def test_name_uniqueness_with_organization_name(self):
        organization = OrganizationFactory(
            internal_id='AAA',
            name_cs='AAA',
            name_en='AAA',
            short_name='AA',
        )

        with pytest.raises(ValidationError):
            OrganizationAltNameFactory(organization=organization, name='AAA')
        with pytest.raises(ValidationError):
            OrganizationAltNameFactory(organization=organization, name='aaa')
        with pytest.raises(ValidationError):
            OrganizationAltNameFactory(organization=organization, name='aAa')


@pytest.mark.django_db
class TestOrganization:
    def test_short_name_uniqueness(self, organizations):
        OrganizationFactory(
            ext_id=998,
            name_cs='CCC',
            name_en='CCC',
            short_name='CC',
        )
        with pytest.raises(IntegrityError):
            # cannot create name with the same short_name and empty
            OrganizationFactory(
                ext_id=999,
                name_cs='DDD',
                name_en='DDD',
                short_name='AA',
            )

    def test_short_name_uniqueness_same_source(self, organizations):
        source = DataSource.objects.create(short_name='foo', type=DataSource.TYPE_API)
        OrganizationFactory(
            ext_id=None,
            name_cs='CCC',
            name_en='CCC',
            short_name='CC',
            source=source,
        )
        with pytest.raises(IntegrityError):
            # cannot create name with the same short_name and same source
            OrganizationFactory(
                ext_id=None,
                name_cs='DDD',
                name_en='DDD',
                short_name='CC',
                source=source,
            )

    def test_short_name_uniqueness_different_source(self, organizations):
        source = DataSource.objects.create(short_name='foo', type=DataSource.TYPE_API)
        OrganizationFactory(
            ext_id=None,
            name_cs='CCC',
            name_en='CCC',
            short_name='CC',
            source=source,
        )
        OrganizationFactory(
            ext_id=None,
            name_cs='DDD',
            name_en='DDD',
            short_name='CC',
            source=None,
        )
        OrganizationFactory(
            ext_id=None,
            name_cs='AAA',
            name_en='AAA',
            short_name='AA',
            source=source,
        )

    def test_with_altname_uniqueness(self, organizations):
        OrganizationAltNameFactory(organization=organizations[0], name='EEE')

        # Note that full_clean() should be called when editing organization in admin

        with pytest.raises(ValidationError):
            org = Organization(
                ext_id=None,
                name_cs='XXX',
                name_en='YYY',
                short_name='EEE',
                source=None,
            )
            org.full_clean()

        with pytest.raises(ValidationError):
            org = Organization(
                ext_id=None,
                name_cs='XXX',
                name_en='EEE',
                short_name='YYY',
                source=None,
            )
            org.full_clean()

        with pytest.raises(ValidationError):
            org = Organization(
                ext_id=None,
                name_cs='EEE',
                name_en='XXX',
                short_name='YYY',
                source=None,
            )
            org.full_clean()
