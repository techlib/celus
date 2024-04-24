def all_nibbler_counter_parsers(json_format: bool = False) -> str:
    name = "Json" if json_format else "Tabular"
    return f"static\\.counter[^\\.]+\\.[^\\.]+.{name}"
