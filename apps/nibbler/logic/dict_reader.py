from celus_nibbler.reader import CsvReader, DictReader


def get_dict_reader_from_csv(infile, sheet_num: int = 0) -> DictReader:
    sheets = CsvReader(infile)
    return sheets[sheet_num].dict_reader()
