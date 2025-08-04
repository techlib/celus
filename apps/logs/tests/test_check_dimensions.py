from contextlib import nullcontext

import pytest
from django.core.management import CommandError, call_command

from logs.fake_data import DimensionFactory, DimensionTextFactory
from logs.models import Dimension, DimensionText


@pytest.mark.django_db
class TestCheckDimensions:
    def _check_yop(self):
        assert Dimension.objects.filter(short_name="YOP").exists(), "YOP dimension exists"
        assert set(
            DimensionText.objects.filter(dimension__short_name="YOP").values_list("text", flat=True)
        ).issuperset({f"{i:04}" for i in range(1, 2101)} | {"9999"}), "all YOP values are present"

    @pytest.mark.parametrize("doit", (True, False))
    def test_missing_yop_dim(self, doit):
        args = ["--do-it"] if doit else []
        ctx_mng = nullcontext() if doit else pytest.raises(CommandError)
        with ctx_mng:
            call_command("check_dimensions", *args)

        if doit:
            self._check_yop()
            # Second call should pass
            call_command("check_dimensions", *args)

    @pytest.mark.parametrize("doit", (True, False))
    def test_missing_yop_text(self, doit):
        DimensionFactory(short_name="YOP")

        args = ["--do-it"] if doit else []
        ctx_mng = nullcontext() if doit else pytest.raises(CommandError)
        with ctx_mng:
            call_command("check_dimensions", *args)

        if doit:
            self._check_yop()
            # Second call should pass
            call_command("check_dimensions", *args)

    @pytest.mark.parametrize("doit", (True, False))
    def test_yop_ready(self, doit):
        dimension = DimensionFactory(short_name="YOP")
        DimensionTextFactory(dimension=dimension, text="9999")
        for i in range(1, 2101):
            DimensionTextFactory(dimension=dimension, text=f"{i:04}")

        # Should not raise exception
        args = ["--do-it"] if doit else []
        call_command("check_dimensions", *args)

        self._check_yop()
        # Second call should pass
        call_command("check_dimensions", *args)
