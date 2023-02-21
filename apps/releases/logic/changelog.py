import re

from django.conf import settings


def get_changelog_entries():
    with open(settings.BASE_DIR / "CHANGELOG.md", 'rt', encoding='utf-8') as f:
        return parse_changelog(f.read())


def parse_changelog(content: str):
    list_of_releases = content.split("## [")
    list_of_releases.pop(0)
    releases = []
    for release in list_of_releases:
        rel_parts = release.split("\n\n", 1)
        if m := re.match(
            r"^((?:\d+\.\d+\.\d+)|Unreleased)](?:\s*-\s*(\d{4}-\d{2}-\d{2}))?\s*$", rel_parts[0]
        ):
            version = m.group(1)
            date = m.group(2)
        else:
            raise ValueError("Cannot parse release header: " + rel_parts[0])
        rel_dict = {"version": version, "date": date, "markdown": rel_parts[1]}
        releases.append(rel_dict)
    return releases
