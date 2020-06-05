from django.urls import reverse


def test_reverse_admin():
    # '/custom-admin/' is configured in CELUS_ADMIN_SITE_PATH
    # which is set in pytest.ini
    assert "/custom-admin/" == reverse("admin:index")
