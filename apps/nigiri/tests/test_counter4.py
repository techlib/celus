import pytest

from pathlib import Path

from nigiri.client import Sushi4Client


class TestErrors:
    @pytest.mark.parametrize(
        "filename,code,severity",
        (
            ("4_BR2_invalid_location1.xml", 1110, "Error"),
            ("4_BR2_not_supported1.xml", 3000, "Error"),
            ("4_BR2_service_not_available1.xml", 1000, "Error"),  # "Fatal" -> "Error"
            ("4_BR2_unauthorized1.xml", 2000, "Error"),
            ("4_BR2_unauthorized2.xml", 2010, "Error"),
            ("4_PR1_invalid_requestor.xml", 2000, "Error"),
            ("sushi_1111.xml", 1111, "Error"),
            ("sushi_1111-severity-number.xml", 1111, "Error"),  # "4" -> "Error"
            ("sushi_1111-severity-missing.xml", 1111, "Error"),
            ("sushi_3030.xml", 3030, "Error"),
        ),
    )
    def test_error_extraction(self, filename, code, severity):

        client = Sushi4Client("https://example.com/", "user")

        with (Path(__file__).parent / "data/counter4/" / filename).open("rb") as f:
            errors = client.extract_errors_from_data(f)
            assert len(errors) == 1
            error = errors[0]
            assert int(error.code) == code
            assert error.severity == severity
