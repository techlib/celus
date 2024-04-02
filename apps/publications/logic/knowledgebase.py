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
