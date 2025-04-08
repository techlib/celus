import typing


def get_url(knowledgebase: dict, counter_version: int) -> typing.Optional[str]:
    """Returns url from knowledgebase dict"""
    try:
        providers = [
            e for e in knowledgebase["providers"] if e["counter_version"] == counter_version
        ]
        return providers[0]["provider"]["url"]
    except (KeyError, IndexError):
        return None


def get_counter_reports(
    knowledgebase: typing.Optional[dict],
) -> typing.List[typing.Tuple[int, str]]:
    """Returns all counter reports from knowledgebase dict"""
    if not knowledgebase:
        return []
    res = []
    try:
        for provider in knowledgebase["providers"]:
            for art in provider["assigned_report_types"]:
                res.append((provider["counter_version"], art["report_type"]))
    except (KeyError, IndexError):
        return []

    return res
