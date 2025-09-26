from functools import cached_property
from itertools import groupby
from time import monotonic
from typing import Any, Callable, Dict, Iterable, List, NamedTuple, Optional, Tuple

from django.conf import settings
from django.db.models import Q
from hcube.api.models.aggregation import Count
from hcube.api.models.transforms import StoredMap
from organizations.models import Organization
from publications.models import Platform
from tags.models import AccessibleBy, Tag, TitleTag

from logs.cubes import AccessLogCube, ch_backend
from logs.models import AccessLog, DimensionText, ReportType


class Noop:
    def __getattr__(self, _):
        return self

    def __call__(self, arg, *args, **kwargs):
        return arg

    def isatty(self):
        return False


# Create a singleton instance
Noop = Noop()


class AnalyticalExportBackend:
    NAME = "dummy"

    # These are the columns to be exported from AccessLogs, order-sensitive.
    # Dimension columns are included and named automatically through report_type.
    # key -> attribute on AccessLog, value -> column name in the export
    COLS = {
        "metric_id": "metric_id",
        "metric__short_name": "metric__short_name",
        "organization_id": "organization_id",
        "organization__name": "organization__name",
        "platform_id": "platform_id",
        "platform__name": "platform__name",
        "target_id": "title_id",
        "target__name": "title__name",
        "target__pub_type": "title__pub_type",
        "target__isbn": "title__isbn",
        "target__issn": "title__issn",
        "target__eissn": "title__eissn",
        "target__doi": "title__doi",
        "value": "value",
        "date": "date",
        "import_batch_id": "import_batch_id",
    }

    # These columns will be taken out and placed after dimension columns
    DIM_BEFORE = ("value", "date", "import_batch_id")

    def __init__(
        self,
        report_type: ReportType,
        organization: Optional[Organization] = None,
        platform: Optional[Platform] = None,
        force: bool = False,
        tags: bool = False,
        no_internal_tags: bool = False,
        output=None,
        **kwargs,
    ):
        self.rt = report_type
        self.organization = organization
        self.platform = platform
        self.force = force
        self.tags = tags
        self.no_internal_tags = no_internal_tags
        self.output = output
        self.stderr = kwargs.get("stderr", Noop)
        self.style = kwargs.get("style", Noop)
        self.cols: Dict[str, str] = self.COLS.copy()
        self._tag_cols = []

        append = {k: self.cols.pop(k) for k in self.DIM_BEFORE}
        if self.tags:
            self._tag_cols.append("tags")
            if not self.no_internal_tags:
                self._tag_cols.append("internal_tags")
            if not self.organization:
                self._tag_cols.append("organization_tags")
            if not self.platform:
                self._tag_cols.append("platform_tags")
            append.update({k: k for k in self._tag_cols})

        for n, dim in enumerate(self.rt.dimensions_sorted):
            self.cols[f"dim{n + 1}"] = str(dim).lower()
        self.cols.update(append)

    def _pre_export(self, cols: Iterable[str]):
        pass

    def _export_row(self, row: Dict[str, Any]):
        pass

    def get_dim_texts(self) -> Dict[str, Dict[int, str]]:
        dim_text_maps = {}
        for i, dim in enumerate(self.rt.dimensions_sorted):
            d = {}
            for id, text in (
                DimensionText.objects.filter(dimension=dim).values_list("id", "text").iterator()
            ):
                d[id] = text
            dim_text_maps[f"dim{i + 1}"] = d
        return dim_text_maps

    @cached_property
    def title_tags_dict(self) -> Optional[Dict[int, Tuple[str, bool]]]:
        if not self.tags:
            return None

        tag_qs = Tag.objects.prefetch_related("tag_class")
        filters = Q(can_see=AccessibleBy.EVERYBODY)
        if self.organization:
            filters |= Q(can_see=AccessibleBy.ORG_ADMINS, owner_org=self.organization)
        else:
            filters |= Q(can_see=AccessibleBy.ORG_ADMINS)
            filters |= Q(can_see=AccessibleBy.CONS_ADMINS)
        if self.no_internal_tags:
            filters &= Q(tag_class__internal=False)
        tag_qs = tag_qs.filter(filters)

        tags_dict: Dict[int, str] = {tag.id: tag.full_name for tag in tag_qs}

        title_tag_qs = TitleTag.objects.filter(tag__in=tag_qs)
        title_tags = title_tag_qs.values_list("target_id", "tag_id").order_by("target_id")

        internal = set()
        if not self.no_internal_tags:
            internal = set(tag_qs.filter(tag_class__internal=True).values_list("id", flat=True))
        return {
            title_id: [(tags_dict[tag_id], tag_id in internal) for _, tag_id in tag_ids]
            for title_id, tag_ids in groupby(title_tags, key=lambda x: x[0])
        }

    @cached_property
    def org_tags_dict(self):
        return {
            org.id: [
                org_tag.tag.full_name
                for org_tag in org.organizationtag_set.all()
                if org_tag.tag.can_see <= AccessibleBy.CONS_ADMINS
            ]
            for org in Organization.objects.prefetch_related("organizationtag_set").all()
        }

    @cached_property
    def platform_tags_dict(self):
        return {
            platform.id: [
                plat_tag.tag.full_name
                for plat_tag in platform.platformtag_set.all()
                if plat_tag.tag.can_see <= AccessibleBy.CONS_ADMINS
            ]
            for platform in Platform.objects.prefetch_related("platformtag_set").all()
        }

    def from_list(self, lst: Optional[List]):
        return [] if lst is None else lst

    def get_tags(self, title_id, org_id, platform_id):
        title_tags_dict = self.title_tags_dict
        if title_tags_dict is None:
            return {}
        row = {
            "tags": (
                self.from_list([tag for tag, internal in title_tags_dict[title_id] if not internal])
                if title_id and title_id in title_tags_dict
                else self.from_list(None)
            )
        }
        if not self.no_internal_tags:
            row["internal_tags"] = (
                self.from_list([tag for tag, internal in title_tags_dict[title_id] if internal])
                if title_id and title_id in title_tags_dict
                else self.from_list(None)
            )
        if not self.organization:
            row["organization_tags"] = self.from_list(self.org_tags_dict[org_id])
        if not self.platform:
            row["platform_tags"] = self.from_list(self.platform_tags_dict[platform_id])
        return row

    def _export(self, progress_monitor: Optional[Callable[[int, int], None]] = None) -> int:
        self.stderr.write("Waiting for DB...")
        timed = monotonic()

        self._pre_export(self.cols.values())

        dim_text_maps = self.get_dim_texts()
        total_count = self.count()

        self.stderr.write(f"Loaded in {monotonic() - timed:.3f}s... Starting")

        timed = monotonic()
        for progress, row in enumerate(self.rows()):
            progress += 1
            row_dict = {}
            for k, target_k in self.cols.items():
                if k in self._tag_cols:
                    # tags will be dealt with separately later in the loop
                    continue
                row_dict[target_k] = getattr(row, k)
                if (dim_text_map := dim_text_maps.get(k)) and (val := row_dict[target_k]):
                    row_dict[target_k] = dim_text_map[val]

            if self.tags:
                row_dict.update(
                    self.get_tags(
                        row_dict["title_id"], row_dict["organization_id"], row_dict["platform_id"]
                    )
                )

            self._export_row(row_dict)  # order

            if progress % 100000 == 1 or progress == total_count:
                if progress_monitor:
                    progress_monitor(progress, total_count)
                else:
                    avg = progress / (monotonic() - timed)
                    remaining = (total_count - progress) / avg
                    mins, secs = divmod(remaining, 60)
                    self.stderr.write(
                        ("\r\033[0K" if self.stderr.isatty() else "")
                        + r"/-\|"[progress // 10000 % 4]
                        + f" {progress / total_count * 100: >6,.2f}%  ({progress} / {total_count})"
                        f"   avg. {avg:,.0f} rows/s"
                        f"   ETA: {mins:.0f}m {secs:.0f}s",
                        ending="" if self.stderr.isatty() else "\n",
                    )
        if progress_monitor:
            progress_monitor(total_count, total_count)
        self.stderr.write("\n\nDone.")
        return total_count

    def rows(self):
        cols = [k for k in self.cols.keys() if not k.endswith("tags")]
        return (
            self._rows_clickhouse() if settings.CLICKHOUSE_QUERY_ACTIVE else self._rows_django(cols)
        )

    def count(self):
        return (
            ch_backend.get_one_record(self._query_clickhouse().aggregate(count=Count())).count
            if settings.CLICKHOUSE_QUERY_ACTIVE
            else self._query_django().count()
        )

    def _query_django(self):
        return self._query_filter(AccessLog.objects.all())

    def _query_clickhouse(self):
        return self._query_filter(AccessLogCube.query())

    def _query_filter(self, query):
        query = query.filter(report_type_id=self.rt.id)
        if self.organization:
            query = query.filter(organization_id=self.organization.id)
        if self.platform:
            query = query.filter(platform_id=self.platform.id)
        return query

    def _rows_django(self, cols: List[str]) -> Iterable[NamedTuple]:
        return self._query_django().values_list(*cols, named=True).iterator(chunk_size=1000)

    def _rows_clickhouse(self) -> Iterable[NamedTuple]:
        query = self._query_clickhouse().transform(
            target__name=StoredMap("target_id", "title", "name"),
            target__issn=StoredMap("target_id", "title", "issn"),
            target__eissn=StoredMap("target_id", "title", "eissn"),
            target__isbn=StoredMap("target_id", "title", "isbn"),
            target__doi=StoredMap("target_id", "title", "doi"),
            target__pub_type=StoredMap("target_id", "title", "pub_type"),
            platform__name=StoredMap("platform_id", "platform", "name"),
            organization__name=StoredMap("organization_id", "organization", "name"),
            metric__short_name=StoredMap("metric_id", "metric", "short_name"),
        )
        return ch_backend.get_records(query, streaming=True)

    def export(self) -> int:
        raise NotImplementedError

    def show_import_instructions(self, dbs, **kwargs):
        for db in dbs:
            self.stderr.style_func = None
            self.stderr.write("\n---")
            self.stderr.write(self.style.WARNING(f"Import to: {db.NAME}"))
            self.stderr.write("")
            db = db(
                self.cols,
                report_type=self.rt,
                organization=self.organization,
                platform=self.platform,
            )
            tb_name = "report_" + self.rt.short_name
            self.stderr.write(db.generate_table(tb_name))
            self.stderr.write("")
            self.stderr.write(db.generate_import(tb_name, self.NAME, **kwargs))
