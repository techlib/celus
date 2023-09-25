import pytest

from core.logic.bins import bin_hits


class TestLogicBins:
    @pytest.mark.parametrize(
        'data, bins',
        [
            ({15: 1}, {(11, 20): 1}),
            ({15: 1, 18: 5}, {(11, 20): 6}),
            ({15: 1, 18: 5, 105: 3}, {(11, 20): 6, (101, 200): 3}),
            ({1000: 1}, {(901, 1000): 1}),
        ],
    )
    def test_bins(self, data, bins):
        assert bin_hits(data) == bins

    def test_bins_with_histogram_bins(self):
        assert bin_hits({15: 1, 18: 5, 105: 3}, histogram_bins=((0, 15), (16, 1000))) == {
            (16, 1000): 8,
            (0, 15): 1,
        }
