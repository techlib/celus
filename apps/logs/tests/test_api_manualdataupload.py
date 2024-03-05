from pathlib import Path
from unittest.mock import patch

import pytest
from core.tests.conftest import *  # noqa
from django.core.files.base import ContentFile
from django.urls import reverse
from organizations.fake_data import OrganizationFactory

from logs.fake_data import MetricFactory
from logs.models import AccessLog, ImportBatch, ManualDataUpload, MduMethod, MduState
from logs.tasks import import_manual_upload_data, prepare_preflight
from test_scenarios.basic import (  # noqa - fixtures
    basic1,
    clients,
    counter_report_types,
    data_sources,
    identities,
    metrics,
    organizations,
    parser_definitions,
    platforms,
    report_types,
    users,
)


@pytest.mark.django_db
class TestManualUploadForCounterData:
    @pytest.mark.parametrize(["hash_matches"], [(True,), (False,)])
    @pytest.mark.parametrize(
        ["filename", "report_code"],
        (
            ("counter4/counter4_br2.tsv", "br2"),
            ("counter5/counter5_table_dr.csv", "dr"),
            ("counter5/counter5_table_dr.tsv", "dr"),
            ("counter5/counter5_table_pr.csv", "pr"),
            ("counter5/counter5_tr_test1.json", "tr"),
        ),
    )
    def test_counter_uploads(
        self,
        basic1,
        organizations,
        platforms,
        counter_report_types,
        clients,
        tmp_path,
        settings,
        filename,
        report_code,
        hash_matches,
    ):
        with (Path(__file__).parent / "data" / filename).open() as f:
            data_file = ContentFile(f.read())
            data_file.name = f"something.{filename.split('.')[-1]}"

        organization = organizations["master"]
        platform = platforms["master"]
        settings.MEDIA_ROOT = tmp_path

        # upload the data
        response = clients["master_admin"].post(
            reverse("manual-data-upload-list"),
            data={
                "platform": platform.id,
                "organization": organization.pk,
                "data_file": data_file,
                "method": MduMethod.COUNTER,
            },
        )
        assert response.status_code == 201

        mdu = ManualDataUpload.objects.get(pk=response.json()["pk"])

        # confirm report type
        response = clients["master_admin"].post(
            reverse("manual-data-upload-confirm", args=(mdu.pk,)),
        )
        assert response.status_code == 200

        if not hash_matches:
            mdu.checksum = "foobarbaz"
            mdu.save()

        # calculate preflight in celery
        with patch("core.models.SourceFileMixin._send_error_mail") as mail_mock, patch(
            "logs.tasks.async_mail_admins"
        ) as mail_admins_mock:
            prepare_preflight(mdu.pk)

        response = clients["master_admin"].get(reverse("manual-data-upload-detail", args=(mdu.pk,)))
        assert response.status_code == 200
        data = response.json()
        assert "preflight" in data
        if hash_matches:
            assert "hits_total" in data["preflight"]
            assert data["preflight"]["log_count"] > 0
            for month_data in data["preflight"]["months"].values():
                assert set(month_data.keys()) == {
                    "new",
                    "this_month",
                    "prev_year_avg",
                    "prev_year_month",
                }
            assert not mail_mock.called, "email to admin was not sent"
        else:
            assert data["error"] == "general"
            assert mail_mock.called, "email to admin was sent from checksum mismatch"
            assert mail_admins_mock.delay.called, "email to admins was sent from MDU preflight fail"

    @pytest.mark.parametrize(["hash_matches"], [(True,), (False,)])
    @pytest.mark.parametrize(
        ["filename", "report_code"],
        (
            ("counter4/counter4_br2.tsv", "br2"),
            ("counter5/counter5_table_dr.csv", "dr"),
            ("counter5/counter5_table_dr.tsv", "dr"),
            ("counter5/counter5_table_pr.csv", "pr"),
            ("counter5/counter5_tr_test1.json", "tr"),
        ),
    )
    def test_counter_manual_import(
        self,
        basic1,
        organizations,
        platforms,
        report_types,
        clients,
        tmp_path,
        settings,
        filename,
        report_code,
        hash_matches,
    ):
        with (Path(__file__).parent / "data" / filename).open() as f:
            data_file = ContentFile(f.read())
            data_file.name = f"something.{filename.split('.')[-1]}"

        organization = organizations["master"]
        platform = platforms["master"]
        settings.MEDIA_ROOT = tmp_path

        # upload the data
        response = clients["master_admin"].post(
            reverse("manual-data-upload-list"),
            data={
                "platform": platform.id,
                "organization": organization.pk,
                "data_file": data_file,
                "method": MduMethod.COUNTER,
            },
        )
        assert response.status_code == 201
        mdu = ManualDataUpload.objects.get(pk=response.json()["pk"])

        # check report type
        response = clients["master_admin"].get(reverse("manual-data-upload-detail", args=(mdu.pk,)))
        assert response.status_code == 200
        assert response.json()["report_type"]["pk"] == report_types[report_code].id

        # confirm report type
        response = clients["master_admin"].post(
            reverse("manual-data-upload-confirm", args=(mdu.pk,)),
        )
        assert response.status_code == 200

        # Calculate preflight in celery
        prepare_preflight(mdu.pk)

        mdu.refresh_from_db()
        if not hash_matches:
            mdu.checksum = "foobarbaz"
            mdu.save()

        # try the import - the following just starts the import
        response = clients["master_admin"].post(
            reverse("manual-data-upload-import-data", args=(mdu.pk,))
        )
        assert response.status_code == 200
        assert "msg" in response.json()
        # without celery, we need to process it ourselves
        with patch("core.models.SourceFileMixin._send_error_mail") as mail_mock:
            import_manual_upload_data(mdu.pk, mdu.user.pk)

        # now we can get the details
        response = clients["master_admin"].get(reverse("manual-data-upload-detail", args=(mdu.pk,)))
        assert response.status_code == 200
        data = response.json()
        if hash_matches:
            assert data["error"] is None
            assert not mail_mock.called, "email to admin was not sent"
        else:
            assert data["error"] == "import-error"
            assert "checksum" in data["error_details"]["exception"]
            assert mail_mock.called, "email to admin was sent"

    @pytest.mark.parametrize(
        ["filename", "create_fails", "preflight_fails"],
        (
            pytest.param(
                "counter5/counter5_tr_test1_wrong_id.json",
                True,
                True,
                id="Nibbler fails on wrong report ID",
            ),
            pytest.param(
                "counter5/counter5_table_pr_wrong_value.csv",
                False,
                True,
                id="Nibbler fails during preflight",
            ),
        ),
    )
    def test_failures(
        self,
        basic1,
        counter_report_types,
        organizations,
        platforms,
        clients,
        tmp_path,
        settings,
        filename,
        create_fails,
        preflight_fails,
    ):
        with (Path(__file__).parent / "data" / filename).open() as f:
            data_file = ContentFile(f.read())
            data_file.name = f"something.{filename.split('.')[-1]}"

        organization = organizations["master"]
        platform = platforms["master"]
        settings.MEDIA_ROOT = tmp_path

        # upload the data
        response = clients["master_admin"].post(
            reverse("manual-data-upload-list"),
            data={
                "platform": platform.id,
                "organization": organization.pk,
                "data_file": data_file,
                "method": MduMethod.COUNTER,
            },
        )
        if create_fails:
            assert response.status_code == 400
            return
        else:
            assert response.status_code == 201

        mdu = ManualDataUpload.objects.get(pk=response.json()["pk"])

        # confirm report type
        response = clients["master_admin"].post(
            reverse("manual-data-upload-confirm", args=(mdu.pk,)),
        )
        assert response.status_code == 200

        # calculate preflight in celery
        prepare_preflight(mdu.pk)

        mdu.refresh_from_db()
        if preflight_fails:
            assert mdu.state == MduState.PREFAILED
        else:
            assert mdu.state == MduState.PREFLIGHT

        # try the import
        response = clients["master_admin"].post(
            reverse("manual-data-upload-import-data", args=(mdu.pk,))
        )

        if preflight_fails:
            assert response.status_code == 400
        else:
            assert response.status_code == 200

    @pytest.mark.parametrize(
        ["filename", "months"],
        (
            pytest.param(
                "counter5/counter5_table_tr_empty.csv",
                {
                    "2017-01-01",
                    "2017-02-01",
                    "2017-03-01",
                    "2017-04-01",
                    "2017-05-01",
                    "2017-06-01",
                },
                id="Months are show from header of TR report",
            ),
            pytest.param(
                "counter5/counter5_table_dr_empty.csv",
                {
                    "2017-01-01",
                    "2017-02-01",
                    "2017-03-01",
                    "2017-04-01",
                    "2017-05-01",
                    "2017-06-01",
                },
                id="Months are show from header of DR report",
            ),
            pytest.param(
                "counter5/counter5_table_pr_empty.csv",
                {
                    "2017-01-01",
                    "2017-02-01",
                    "2017-03-01",
                    "2017-04-01",
                    "2017-05-01",
                    "2017-06-01",
                },
                id="Months are show from header of TR report",
            ),
        ),
    )
    def test_empty_data(
        self,
        basic1,
        organizations,
        counter_report_types,
        platforms,
        clients,
        tmp_path,
        settings,
        filename,
        months,
    ):
        with (Path(__file__).parent / "data" / filename).open() as f:
            data_file = ContentFile(f.read())
            data_file.name = f"something.{filename.split('.')[-1]}"

        organization = organizations["master"]
        platform = platforms["master"]
        settings.MEDIA_ROOT = tmp_path

        # upload the data
        response = clients["master_admin"].post(
            reverse("manual-data-upload-list"),
            data={
                "platform": platform.id,
                "organization": organization.pk,
                "data_file": data_file,
                "method": MduMethod.COUNTER,
            },
        )
        assert response.status_code == 201
        mdu = ManualDataUpload.objects.get(pk=response.json()["pk"])

        # confirm report type
        response = clients["master_admin"].post(
            reverse("manual-data-upload-confirm", args=(mdu.pk,)),
        )
        assert response.status_code == 200

        # calculate preflight in celery
        prepare_preflight(mdu.pk)

        mdu.refresh_from_db()
        assert mdu.state == MduState.PREFLIGHT
        assert set(mdu.preflight["months"].keys()) == months
        for month_data in mdu.preflight["months"].values():
            assert month_data["new"] == {"sum": 0, "count": 0}

        response = clients["master_admin"].post(
            reverse("manual-data-upload-import-data", args=(mdu.pk,))
        )
        assert response.status_code == 200

        # process data
        response = clients["master_admin"].post(
            reverse("manual-data-upload-import-data", args=(mdu.pk,))
        )
        assert response.status_code == 200

        import_manual_upload_data(mdu.pk, mdu.user.pk)

        mdu.refresh_from_db()
        assert mdu.state == MduState.IMPORTED

        response = clients["master_admin"].get(reverse("manual-data-upload-detail", args=(mdu.pk,)))
        assert response.status_code == 200
        assert months == {e["date"] for e in response.data["import_batches"]}

    def test_wrong_encoding(
        self,
        basic1,
        organizations,
        counter_report_types,
        platforms,
        clients,
        tmp_path,
        settings,
    ):
        with (Path(__file__).parent / "data/counter5/TR-wrong-encoding.csv").open("rb") as f:
            data_file = ContentFile(f.read())
            data_file.name = "TR-wrong-encoding.csv"

        organization = organizations["master"]
        platform = platforms["master"]
        settings.MEDIA_ROOT = tmp_path

        # upload the data
        response = clients["master_admin"].post(
            reverse("manual-data-upload-list"),
            data={
                "platform": platform.id,
                "organization": organization.pk,
                "data_file": data_file,
                "method": MduMethod.COUNTER,
            },
        )
        assert response.status_code == 400
        assert "encoding_error" in response.data

    def test_upload_of_private_platform_from_non_owner_organization(
        self,
        basic1,
        organizations,
        counter_report_types,
        platforms,
        clients,
        tmp_path,
        settings,
    ):
        with (Path(__file__).parent / "data/counter5/counter5_table_dr.tsv").open("rb") as f:
            data_file = ContentFile(f.read())
            data_file.name = "dr.csv"

        settings.MEDIA_ROOT = tmp_path

        # upload the data
        # note that standalone and branch platforms are private
        response = clients["master_admin"].post(
            reverse("manual-data-upload-list"),
            data={
                "platform": platforms["standalone"].pk,
                "organization": organizations["branch"].pk,
                "data_file": data_file,
                "method": MduMethod.COUNTER,
            },
        )
        assert response.status_code == 400

    def test_change_of_organization_to_unrelated_private_platform_in_preflight(
        self,
        basic1,
        organizations,
        counter_report_types,
        platforms,
        clients,
        tmp_path,
        settings,
    ):
        with (Path(__file__).parent / "data/counter5/counter5_table_dr.tsv").open("rb") as f:
            data_file = ContentFile(f.read())
            data_file.name = "dr.csv"

        settings.MEDIA_ROOT = tmp_path

        # upload the data
        # note that standalone and branch platforms are private
        response = clients["master_admin"].post(
            reverse("manual-data-upload-list"),
            data={
                "platform": platforms["standalone"].pk,
                "organization": organizations["standalone"].pk,
                "data_file": data_file,
                "method": MduMethod.COUNTER,
            },
        )
        assert response.status_code == 201
        mdu = ManualDataUpload.objects.get(pk=response.json()["pk"])

        # confirm report type
        response = clients["master_admin"].post(
            reverse("manual-data-upload-confirm", args=(mdu.pk,)),
        )
        assert response.status_code == 200

        response = clients["master_admin"].post(
            reverse("manual-data-upload-preflight", args=(mdu.pk,)),
            {"organization_id": organizations["branch"].pk},
        )

        assert response.status_code == 403


@pytest.mark.django_db
class TestManualUploadControlledMetrics:
    def test_can_import(
        self, basic1, organizations, platforms, counter_report_types, clients, tmp_path, settings
    ):
        cr_type = counter_report_types["tr"]
        with (Path(__file__).parent / "data/counter5/counter5_tr_test1.json").open() as f:
            data_file = ContentFile(f.read())
            data_file.name = "counter5_tr_test1.json"

        organization = organizations["master"]
        platform = platforms["master"]
        settings.MEDIA_ROOT = tmp_path

        metrics = [
            "Total_Item_Investigations",
            "Total_Item_Requests",
            "Unique_Item_Investigations",
            "Unique_Item_Requests",
            "Unique_Title_Investigations",
            "Unique_Title_Requests",
        ]
        metrics_objs = [MetricFactory(short_name=e) for e in metrics]

        # upload the data
        response = clients["master_admin"].post(
            reverse("manual-data-upload-list"),
            data={
                "platform": platform.id,
                "organization": organization.pk,
                "data_file": data_file,
                "method": MduMethod.COUNTER,
            },
        )
        assert response.status_code == 201
        mdu = ManualDataUpload.objects.get(pk=response.json()["pk"])

        # confirm report type
        response = clients["master_admin"].post(
            reverse("manual-data-upload-confirm", args=(mdu.pk,)),
        )
        assert response.status_code == 200

        response = clients["master_admin"].post(
            reverse("manual-data-upload-preflight", args=(mdu.pk,)),
            {"organization_id": organizations["master"].pk},
        )
        assert mdu.organization.pk == organizations["master"].pk
        assert response.status_code == 200
        prepare_preflight(mdu.pk)

        response = clients["master_admin"].get(reverse("manual-data-upload-detail", args=(mdu.pk,)))
        assert response.status_code == 200
        # Should be able to import
        assert response.data["can_import"] is True
        assert len(response.data["report_type"]["controlled_metrics"]) == 0
        assert set(response.data["preflight"]["metrics"].keys()) == set(metrics)

        # mark report type as controlled
        cr_type.report_type.controlled_metrics.set(metrics_objs[:2])

        # regenerate preflight with different organization
        response = clients["master_admin"].post(
            reverse("manual-data-upload-preflight", args=(mdu.pk,)),
            {"organization_id": organizations["branch"].pk},
        )
        assert response.status_code == 200
        mdu.refresh_from_db()
        assert mdu.organization.pk == organizations["branch"].pk
        prepare_preflight(mdu.pk)

        response = clients["master_admin"].get(reverse("manual-data-upload-detail", args=(mdu.pk,)))
        assert response.status_code == 200
        # Should be able to import
        assert response.data["can_import"] is False
        assert len(response.data["report_type"]["controlled_metrics"]) > 0
        assert set(response.data["preflight"]["metrics"].keys()) == set(metrics)

        # Should fail to import data
        response = clients["master_admin"].post(
            reverse("manual-data-upload-import-data", args=(mdu.pk,))
        )
        assert response.status_code == 400
        assert response.data == {"error": "can-not-import"}

        # add all required metrics
        cr_type.report_type.controlled_metrics.set(metrics_objs)

        # Get mdu again
        response = clients["master_admin"].get(reverse("manual-data-upload-detail", args=(mdu.pk,)))
        assert response.status_code == 200
        assert response.data["can_import"] is True
        assert len(response.data["report_type"]["controlled_metrics"]) > 0
        assert set(response.data["preflight"]["metrics"].keys()) == set(metrics)

        # Import should pass
        response = clients["master_admin"].post(
            reverse("manual-data-upload-import-data", args=(mdu.pk,))
        )
        assert response.status_code == 200


@pytest.mark.django_db
class TestManualUploadConflicts:
    def test_import_same_file_twice(
        self,
        organizations,
        platforms,
        settings,
        tmp_path,
        counter_report_types,
        report_types,
        clients,
        basic1,
    ):
        with (Path(__file__).parent / "data/counter4/counter4_br2.tsv").open() as f:
            data_file = ContentFile(f.read())
            data_file.name = "something.tsv"

        organization = organizations["master"]
        platform = platforms["master"]
        settings.MEDIA_ROOT = tmp_path

        response = clients["master_admin"].post(
            reverse("manual-data-upload-list"),
            data={
                "platform": platform.id,
                "organization": organization.pk,
                "data_file": data_file,
                "method": MduMethod.COUNTER,
            },
        )
        assert response.status_code == 201
        mdu = ManualDataUpload.objects.get(pk=response.json()["pk"])

        # confirm report type
        response = clients["master_admin"].post(
            reverse("manual-data-upload-confirm", args=(mdu.pk,)),
        )
        assert response.status_code == 200

        # calculate preflight in celery
        prepare_preflight(mdu.pk)

        # process data
        response = clients["master_admin"].post(
            reverse("manual-data-upload-import-data", args=(mdu.pk,))
        )
        assert response.status_code == 200

        # import data (this should be handled via celery)
        import_manual_upload_data(mdu.pk, mdu.user.pk)

        response = clients["master_admin"].get(reverse("manual-data-upload-detail", args=(mdu.pk,)))
        assert response.status_code == 200
        batches = sorted(e["pk"] for e in response.data["import_batches"])
        batches_months = sorted(e["date"] for e in response.data["import_batches"])

        # Upload the same data
        data_file.seek(0)

        response = clients["master_admin"].post(
            reverse("manual-data-upload-list"),
            data={
                "platform": platform.id,
                "organization": organization.pk,
                "data_file": data_file,
                "method": MduMethod.COUNTER,
            },
        )
        assert response.status_code == 201
        mdu = ManualDataUpload.objects.get(pk=response.json()["pk"])

        # confirm report type
        response = clients["master_admin"].post(
            reverse("manual-data-upload-confirm", args=(mdu.pk,)),
        )
        assert response.status_code == 200

        # calculate preflight in celery
        prepare_preflight(mdu.pk)

        # fail preflight
        response = clients["master_admin"].get(reverse("manual-data-upload-detail", args=(mdu.pk,)))
        assert response.status_code == 200
        assert response.data["can_import"] is False
        assert batches_months == sorted(e["month"] for e in response.data["clashing_months"])

        # fail processing
        response = clients["master_admin"].post(
            reverse("manual-data-upload-import-data", args=(mdu.pk,))
        )
        assert response.status_code == 409
        assert batches == sorted(
            e["pk"] for e in response.data["clashing_import_batches"]
        ), "all import batches are in conflict"

    @pytest.mark.skip()
    def test_conflict_with_sushi(self):
        raise NotImplementedError()


@pytest.mark.django_db
class TestManualUploadForRaw:
    def test_multiple_organizations_unauthorized(
        self, platforms, organizations, settings, tmp_path, clients, report_types, basic1
    ):
        with (
            Path(__file__).parent / "data/custom/custom_data-2d-3x2x3-org-isodate.csv"
        ).open() as f:
            data_file = ContentFile(f.read())
            data_file.name = "something.csv"

        organization = organizations["standalone"]
        platform = platforms["standalone"]
        settings.MEDIA_ROOT = tmp_path

        response = clients["admin2"].post(
            reverse("manual-data-upload-list"),
            data={
                "platform": platform.id,
                "organization": organization.pk,
                "report_type_id": report_types["custom1"].pk,
                "data_file": data_file,
                "method": MduMethod.CELUS,
            },
        )
        assert response.status_code == 201
        mdu = ManualDataUpload.objects.get(pk=response.json()["pk"])

        # confirm report type
        response = clients["admin2"].post(
            reverse("manual-data-upload-confirm", args=(mdu.pk,)),
        )
        assert response.status_code == 200

        # calculate preflight in celery
        prepare_preflight(mdu.pk)

        # Check that it is not possible to import
        response = clients["admin2"].get(reverse("manual-data-upload-detail", args=(mdu.pk,)))
        assert response.status_code == 200
        assert response.data["can_import"] is False
        assert response.data["preflight"]["organizations"] == {
            "Org1": {"sum": 315, "count": 18, "pk": None},
            "Org2": {"sum": 347, "count": 18, "pk": None},
        }

        # Try to import it
        response = clients["admin2"].post(reverse("manual-data-upload-import-data", args=(mdu.pk,)))

        assert response.status_code == 403

    @pytest.mark.clickhouse
    @pytest.mark.usefixtures("clickhouse_on_off")
    @pytest.mark.django_db(transaction=True)
    @pytest.mark.parametrize(["organization_set"], [(True,), (False,)])
    def test_multiple_organizations_authorized(
        self,
        platforms,
        organizations,
        settings,
        tmp_path,
        clients,
        report_types,
        basic1,
        organization_set,
    ):
        with (
            Path(__file__).parent / "data/custom/custom_data-2d-3x2x3-org-isodate.csv"
        ).open() as f:
            data_file = ContentFile(f.read())
            data_file.name = "something.csv"

        organization = organizations["standalone"] if organization_set else None
        platform = platforms["shared"]
        settings.MEDIA_ROOT = tmp_path

        post_data = {
            "platform": platform.id,
            "report_type_id": report_types["custom1"].pk,
            "data_file": data_file,
            "method": MduMethod.CELUS,
        }
        if organization_set:
            post_data["organization"] = organization.pk
        response = clients["master_admin"].post(reverse("manual-data-upload-list"), data=post_data)
        assert response.status_code == 201
        mdu = ManualDataUpload.objects.get(pk=response.json()["pk"])

        # confirm report type
        response = clients["master_admin"].post(
            reverse("manual-data-upload-confirm", args=(mdu.pk,)),
        )
        assert response.status_code == 200

        # calculate preflight in celery
        prepare_preflight(mdu.pk)

        # Check that it is not possible to import
        response = clients["master_admin"].get(reverse("manual-data-upload-detail", args=(mdu.pk,)))
        assert response.status_code == 200
        assert response.data["can_import"] is False
        assert response.data["preflight"]["organizations"] == {
            "Org1": {"sum": 315, "count": 18, "pk": None},
            "Org2": {"sum": 347, "count": 18, "pk": None},
        }

        # Try to import it
        response = clients["master_admin"].post(
            reverse("manual-data-upload-import-data", args=(mdu.pk,))
        )

        assert response.status_code == 400

        # Create organizations which are present in the file
        org1 = OrganizationFactory(short_name="Org1", name="Organization1")
        org2 = OrganizationFactory(short_name="Org2", name="Organization2")

        # Try to import it
        response = clients["master_admin"].post(
            reverse("manual-data-upload-import-data", args=(mdu.pk,))
        )
        assert response.status_code == 400, "failed again need to regenrate preflight"

        preflight_data = {"organization_id": organization.pk} if organization else {}
        response = clients["master_admin"].post(
            reverse("manual-data-upload-preflight", args=(mdu.pk,)),
            preflight_data,
        )
        assert response.status_code == 200

        prepare_preflight(mdu.pk)

        # Check that it is not possible to again
        response = clients["master_admin"].get(reverse("manual-data-upload-detail", args=(mdu.pk,)))
        assert response.status_code == 200
        assert response.data["can_import"] is True
        assert response.data["preflight"]["organizations"] == {
            "Org1": {"sum": 315, "count": 18, "pk": org1.pk},
            "Org2": {"sum": 347, "count": 18, "pk": org2.pk},
        }

        response = clients["master_admin"].post(
            reverse("manual-data-upload-import-data", args=(mdu.pk,))
        )
        assert response.status_code == 200, "import should pass"

        mdu.refresh_from_db()
        assert mdu.organization is None, "Organization was unset even when imported from data"

        # Now import should pass
        import_manual_upload_data(mdu.pk, mdu.user.pk)
        mdu.refresh_from_db()
        assert mdu.state == MduState.IMPORTED

        # Check the status
        response = clients["master_admin"].get(reverse("manual-data-upload-detail", args=(mdu.pk,)))
        assert response.status_code == 200
        assert len(response.data["import_batches"]) == 6
        assert response.data["import_batches"][0]["organization"] == "Organization1"
        assert response.data["import_batches"][1]["organization"] == "Organization1"
        assert response.data["import_batches"][2]["organization"] == "Organization1"
        assert response.data["import_batches"][3]["organization"] == "Organization2"
        assert response.data["import_batches"][4]["organization"] == "Organization2"
        assert response.data["import_batches"][5]["organization"] == "Organization2"

        # Try to reimport the same data (to see whether it clashes)
        data_file.seek(0)
        response = clients["master_admin"].post(reverse("manual-data-upload-list"), data=post_data)
        assert response.status_code == 201
        mdu = ManualDataUpload.objects.get(pk=response.json()["pk"])

        # confirm report type
        response = clients["master_admin"].post(
            reverse("manual-data-upload-confirm", args=(mdu.pk,)),
        )
        assert response.status_code == 200

        # calculate preflight in celery
        prepare_preflight(mdu.pk)

        # Check that it is not possible to import
        response = clients["master_admin"].get(reverse("manual-data-upload-detail", args=(mdu.pk,)))
        assert response.status_code == 200
        assert response.data["can_import"] is False
        assert {e["month"] for e in response.data["clashing_months"]} == {
            "2019-01-01",
            "2019-02-01",
            "2019-03-01",
        }

        assert {e["org_id"] for e in response.data["clashing_months"]} == {
            org1.pk,
            org2.pk,
        }

        # Try to import it
        response = clients["master_admin"].post(
            reverse("manual-data-upload-import-data", args=(mdu.pk,))
        )
        assert response.status_code == 409, "failed due to clashing data"

    @pytest.mark.parametrize(["organization_set"], [(True,), (False,)])
    def test_single_org_in_multiple_org_file(
        self,
        platforms,
        organizations,
        settings,
        tmp_path,
        clients,
        report_types,
        basic1,
        organization_set,
    ):
        with (
            Path(__file__).parent / "data/custom/custom_data-2d-3x2x3-org-isodate-single.csv"
        ).open() as f:
            data_file = ContentFile(f.read())
            data_file.name = "something.csv"

        organization = organizations["standalone"] if organization_set else None
        platform = platforms["standalone"]
        settings.MEDIA_ROOT = tmp_path

        post_data = {
            "platform": platform.id,
            "report_type_id": report_types["custom1"].pk,
            "data_file": data_file,
            "method": MduMethod.CELUS,
        }
        if organization_set:
            post_data["organization"] = organization.pk
        response = clients["admin2"].post(reverse("manual-data-upload-list"), data=post_data)
        if organization_set:
            assert response.status_code == 201
        else:
            assert response.status_code == 403
            return

        mdu = ManualDataUpload.objects.get(pk=response.json()["pk"])

        # confirm report type
        response = clients["admin2"].post(
            reverse("manual-data-upload-confirm", args=(mdu.pk,)),
        )
        assert response.status_code == 200

        # calculate preflight in celery
        prepare_preflight(mdu.pk)
        mdu.refresh_from_db()

        assert mdu.preflight["organizations"] is None

        response = clients["admin2"].post(reverse("manual-data-upload-import-data", args=(mdu.pk,)))

        assert response.status_code == 200, "Import should pass"

        ib_count = ImportBatch.objects.count()
        access_log_count = AccessLog.objects.count()
        import_manual_upload_data(mdu.pk, mdu.user.pk)
        mdu.refresh_from_db()
        assert mdu.organization == organizations["standalone"], "organization is set"
        assert ImportBatch.objects.count() == ib_count + 3, "3 ibs created"
        assert AccessLog.objects.count() == access_log_count + 18, "18 logs created"

    @pytest.mark.parametrize(
        [
            "from_organization",
            "to_organization",
            "owner",
            "preflight_user",
            "status",
        ],
        [
            ["standalone", "branch", "su", "su", 200],  # super user
            ["standalone", "branch", "master_admin", "master_admin", 200],  # master admin
            ["root", "branch", "admin1", "admin1", 200],  # admin of two organization
            ["branch", "root", "admin1", "admin1", 200],  # admin of two organization
            ["standalone", "standalone", "admin2", "admin2", 200],  # regenerate with same org
            ["standalone", "branch", "admin2", "admin2", 403],  # assign to restrited org
            ["branch", "standalone", "admin1", "admin2", 403],  # steal from organization
        ],
    )
    def test_preflight_organization_changes(
        self,
        platforms,
        organizations,
        settings,
        tmp_path,
        clients,
        users,
        report_types,
        basic1,
        from_organization,
        to_organization,
        owner,
        preflight_user,
        status,
    ):
        # add admin1 as admin for branch organization in this scenario
        users["admin1"].organizations.add(
            organizations["branch"], through_defaults={"is_admin": True}
        )

        with (Path(__file__).parent / "data/counter5/counter5_table_dr.csv").open() as f:
            data_file = ContentFile(f.read())
            data_file.name = "nibbler.csv"

        platform = platforms["shared"]
        settings.MEDIA_ROOT = tmp_path

        response = clients[owner].post(
            reverse("manual-data-upload-list"),
            data={
                "platform": platform.pk,
                "organization": organizations[from_organization].pk,
                "data_file": data_file,
                "method": MduMethod.COUNTER,
            },
        )
        assert response.status_code == 201
        mdu = ManualDataUpload.objects.get(pk=response.json()["pk"])

        # confirm report type
        response = clients[owner].post(
            reverse("manual-data-upload-confirm", args=(mdu.pk,)),
        )
        assert response.status_code == 200

        # calculate preflight in celery
        prepare_preflight(mdu.pk)

        # try to regenerate preflight
        response = clients[preflight_user].post(
            reverse("manual-data-upload-preflight", args=(mdu.pk,)),
            {"organization_id": organizations[to_organization].pk},
        )
        assert response.status_code == status

    @pytest.mark.parametrize(
        [
            "organization",
            "owner",
            "import_user",
            "status",
        ],
        [
            ["branch", "su", "su", 200],  # super user
            ["branch", "master_admin", "master_admin", 200],  # master admin
            ["root", "admin1", "admin1", 200],  # org admin
            ["standalone", "admin2", "su", 200],  # imported by su
            ["standalone", "admin2", "master_admin", 200],  # imported by master
            ["standalone", "admin2", "admin1", 403],  # imported by other admin
        ],
    )
    def test_import_permissions(
        self,
        platforms,
        organizations,
        settings,
        tmp_path,
        clients,
        users,
        report_types,
        counter_report_types,
        basic1,
        organization,
        owner,
        import_user,
        status,
    ):
        with (Path(__file__).parent / "data/counter5/counter5_table_dr.csv").open() as f:
            data_file = ContentFile(f.read())
            data_file.name = "counter.csv"

        organization = organizations[organization]
        platform = platforms["shared"]
        settings.MEDIA_ROOT = tmp_path

        response = clients[owner].post(
            reverse("manual-data-upload-list"),
            data={
                "platform": platform.pk,
                "organization": organization.pk,
                "data_file": data_file,
                "method": MduMethod.COUNTER,
            },
        )
        assert response.status_code == 201
        mdu = ManualDataUpload.objects.get(pk=response.json()["pk"])

        # confirm report type
        response = clients[owner].post(
            reverse("manual-data-upload-confirm", args=(mdu.pk,)),
        )
        assert response.status_code == 200

        # generate preflight
        response = clients[owner].post(
            reverse("manual-data-upload-preflight", args=(mdu.pk,)),
            {"organization_id": organization.pk},
        )
        assert response.status_code == 200

        # calculate preflight in celery
        prepare_preflight(mdu.pk)

        # try to import
        response = clients[import_user].post(
            reverse("manual-data-upload-import-data", args=(mdu.pk,)),
        )

        assert response.status_code == status

    @pytest.mark.parametrize(
        "file_path,report_type,batch_count,new_method",
        [
            ("data/counter5/counter5_table_dr.csv", "dr", 11, MduMethod.COUNTER),
            ("data/custom/custom_data-nibbler-simple.csv", "custom1", 1, MduMethod.RAW),
        ],
        ids=("counter", "non-counter"),
    )
    def test_raw_workflow(
        self,
        basic1,
        organizations,
        platforms,
        report_types,
        counter_report_types,
        clients,
        parser_definitions,
        tmp_path,
        settings,
        file_path,
        report_type,
        batch_count,
        new_method,
    ):
        with (Path(__file__).parent / file_path).open() as f:
            data_file = ContentFile(f.read())
            data_file.name = "nibbler.csv"

        organization = organizations["master"]
        platform = platforms["brain"]
        settings.MEDIA_ROOT = tmp_path
        settings.ENABLE_RAW_DATA_IMPORT = "All"

        response = clients["master_admin"].post(
            reverse("manual-data-upload-list"),
            data={
                "platform": platform.id,
                "organization": organization.pk,
                "data_file": data_file,
                "method": MduMethod.RAW,
            },
        )
        assert response.status_code == 201
        mdu = ManualDataUpload.objects.get(pk=response.json()["pk"])

        # confirm report type
        response = clients["master_admin"].post(
            reverse("manual-data-upload-confirm", args=(mdu.pk,)),
        )
        assert response.status_code == 200

        # calculate preflight in celery
        prepare_preflight(mdu.pk)

        response = clients["master_admin"].get(reverse("manual-data-upload-detail", args=(mdu.pk,)))
        assert (
            response.data["report_type"]["pk"] == report_types[report_type].pk
        ), "report type was selected"
        assert response.data["clashing_months"] == []
        assert response.data["can_import"] is True
        assert mdu.import_batches.count() == 0

        # process data
        response = clients["master_admin"].post(
            reverse("manual-data-upload-import-data", args=(mdu.pk,))
        )
        assert response.status_code == 200

        # import data (this should be handled via celery)
        import_manual_upload_data(mdu.pk, mdu.user.pk)

        response = clients["master_admin"].get(reverse("manual-data-upload-detail", args=(mdu.pk,)))
        assert response.status_code == 200
        assert response.data["method"] == new_method
        assert response.data["can_import"] is False
        assert mdu.import_batches.count() == batch_count
