import pytest

from pathlib import Path

from nigiri.client import Sushi4Client


class TestErrors:
    @pytest.mark.parametrize(
        "filename,code",
        (
            ("4_BR2_invalid_location1.xml", 1110),
            ("4_BR2_not_supported1.xml", 3000),
            ("4_BR2_service_not_available1.xml", 1000),
            ("4_BR2_unauthorized1.xml", 2000),
            ("4_BR2_unauthorized2.xml", 2010),
            ("sushi_1111.xml", 1111),
            ("sushi_3030.xml", 3030),
        ),
    )
    def test_error_extraction(
        self, filename, code,
    ):

        client = Sushi4Client("https://example.com/", "user")

        with (Path(__file__).parent / "data/counter4/" / filename).open() as f:
            errors = client.extract_errors_from_data(f.read())
            assert len(errors) == 1
            error = errors[0]
            assert int(error.code) == code
