import csv
import typing
from collections import namedtuple
from pathlib import Path
from uuid import UUID

from publications.logic import knowledgebase as kb

if typing.TYPE_CHECKING:
    import counter_registry

WhitelistRecord = namedtuple("WhitelistRecord", ["registry_id", "counter_version", "report_code"])


class Whitelist:
    def __init__(self, path: typing.Optional[str]):
        # in (id, counter_registry_id, counter_version, report) Format
        self.records = []

        if path:
            with Path(path).open() as f:
                reader = csv.DictReader(f)
                for line in reader:
                    version = (
                        51 if line["counter_version"] == "5.1" else int(line["counter_version"])
                    )
                    self.records.append(
                        WhitelistRecord(line["registry_id"], version, line["report_code"])
                    )

        self.registry_id_map = {UUID(e.registry_id): e for e in self.records}

    def update_knowledgebase(
        self, platform: "counter_registry.models.PlatformExtras", knowledgebase: dict
    ) -> bool:
        if override := self.registry_id_map.get(platform.id):
            return kb.update_whitelisted(
                knowledgebase, override.counter_version, override.report_code, True
            )

        return False
