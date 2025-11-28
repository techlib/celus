import pytest
from django.db import IntegrityError
from organizations.fake_data import OrganizationFactory

from ch_export.cubes import ch_export_client
from ch_export.models import AccessLogExport


@pytest.mark.django_db
class TestAccessLogExport:
    @pytest.fixture(params=[True, False])
    def organization(self, request):
        return OrganizationFactory() if request.param else None

    def test_create_populates_ch_database_and_ch_password(self, organization, ch_export_clickhouse):
        """
        When an AccessLogExport is created, it should populate the ch_database and ch_password
        fields.
        It should also create the corresponding Clickhouse database and user.
        """
        exp = AccessLogExport.objects.create(organization=organization)
        assert exp.ch_database != ""
        assert exp.ch_password != ""
        out = ch_export_client.execute(
            "EXISTS DATABASE {db:Identifier}",
            {"db": exp.ch_database},
            settings={"server_side_params": True},
        )
        assert out[0][0]
        out = ch_export_client.execute("SHOW USERS")
        assert exp.ch_database in [user[0] for user in out]

    def test_save_keeps_ch_database_and_ch_password(self, organization):
        exp = AccessLogExport.objects.create(organization=organization)
        original_ch_database = exp.ch_database
        original_ch_password = exp.ch_password
        exp.save()
        assert exp.ch_database == original_ch_database
        assert exp.ch_password == original_ch_password

    def test_export_ensures_creation_of_clickhouse_database_and_user(
        self, organization, ch_export_clickhouse
    ):
        """
        Test that if the database or user disappear after the export is created,
        it will be recreated before new data export is started.
        """
        exp = AccessLogExport.objects.create(organization=organization)
        ch_export_client.execute(f"DROP DATABASE {exp.ch_database}")
        ch_export_client.execute(f"DROP USER {exp.ch_database}")
        assert not ch_export_client.execute(f"EXISTS DATABASE {exp.ch_database}")[0][0]
        exp.create_batch(start_tasks=False)
        assert ch_export_client.execute(f"EXISTS DATABASE {exp.ch_database}")[0][0]
        assert exp.ch_database in [user[0] for user in ch_export_client.execute("SHOW USERS")]

    def test_cannot_create_multiple_exports_without_organization(self):
        AccessLogExport.objects.create()
        with pytest.raises(IntegrityError):
            AccessLogExport.objects.create()
