from collections import Counter
from typing import Tuple, Mapping, Sequence


def bin_hits(
    counter: Mapping[int, int], histogram_bins: Sequence[Tuple[int, int]] = ()
) -> Mapping[Tuple[int, int], int]:
    """
    Takes a counter in the form humber_of_hits => count_of_cases and transforms it into a counter
    (bin_start, bin_end) => count_of_cases. That is e. g. {(0,1): 10, (2,5): 20}, etc.
    The bins should be 'pretty' in that they should have both the start and end well rounded. E.g.
    1_234 should be in bin (1_001, 2_000) and 123_456 in (100_001, 200_000).
    :param counter: input data
    :param histogram_bins: if supplied, it defines some of the bins to be used instead of the
                           generated ones
    :return:

    >>> bin_hits({15: 1})
    Counter({(11, 20): 1})

    >>> bin_hits({15: 1, 18: 5})
    Counter({(11, 20): 6})

    >>> bin_hits({15: 1, 18: 5, 105: 3})
    Counter({(11, 20): 6, (101, 200): 3})

    >>> bin_hits({15: 1, 18: 5, 105: 3}, histogram_bins=((0, 15), (16, 1000)))
    Counter({(16, 1000): 8, (0, 15): 1})

    >>> bin_hits({1000: 1})
    Counter({(901, 1000): 1})
    """
    bin_counter = Counter()
    for hits, count in counter.items():
        for start, end in histogram_bins:
            if start <= hits <= end:
                bin_counter[(start, end)] += count
                break
        else:
            digits = len(str(hits)) - 1
            unit = 10**digits
            if hits == unit:
                # for example 10_000 hits would end up between 1 and 10_000 which would be strange
                digits -= 1
                unit = 10**digits
            start = unit * ((hits - 1) // unit)
            end = start + unit
            start += 1
            bin_counter[(start, end)] += count
    return bin_counter
