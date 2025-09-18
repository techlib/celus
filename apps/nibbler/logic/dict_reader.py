import typing

if typing.TYPE_CHECKING:
    from celus_nibbler.reader import DictReader


def get_dict_reader_from_csv(infile, sheet_num: int = 0) -> "DictReader":
    from celus_nibbler.reader import CsvReader  # noqa - slow import

    sheets = CsvReader(infile)
    return sheets[sheet_num].dict_reader()
