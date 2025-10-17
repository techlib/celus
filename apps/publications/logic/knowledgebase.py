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
) -> typing.Dict[typing.Tuple[int, str], typing.Dict[str, typing.Any]]:
    """Returns all counter reports from knowledgebase dict"""
    if not knowledgebase:
        return {}
    res = {}
    try:
        for provider in knowledgebase["providers"]:
            for art in provider["assigned_report_types"]:
                res[(provider["counter_version"], art["report_type"])] = art
    except (KeyError, IndexError):
        return {}

    return res


def get_provider_for_counter_version(
    knowledgebase: dict, counter_version: int
) -> typing.Optional[dict]:
    """Returns provider for counter version from knowledgebase dict"""
    return next(
        (
            e
            for e in knowledgebase.get("providers", [])
            if e.get("counter_version") == counter_version
        ),
        None,
    )


def is_report_type_whitelisted(provider: dict, report_type: str) -> bool:
    """Returns True if report type is whitelisted for the provider"""
    if not provider:
        return False
    if rec := next(
        (
            e
            for e in provider.get("assigned_report_types", [])
            if e.get("report_type") == report_type
        ),
        None,
    ):
        return rec.get("whitelisted", False)
    return False


def update_whitelisted(
    knowledgebase: dict, counter_version: int, report_code: str, whitelisted: bool
) -> bool:
    for provider in knowledgebase["providers"]:
        if provider["counter_version"] == counter_version:
            for art in provider["assigned_report_types"]:
                if art["report_type"] == report_code and art.get("whitelisted") != whitelisted:
                    art["whitelisted"] = whitelisted
                    return True

    return False
