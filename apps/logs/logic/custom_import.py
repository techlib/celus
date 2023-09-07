import logging
import typing
from collections import Counter

from core.models import User
from django.conf import settings
from django.db.transaction import atomic
from django.utils.timezone import now
from organizations.models import Organization

from logs.exceptions import OrganizationNotAllowedToImportRawData, OrganizationNotFound
from logs.logic.data_import import import_counter_records, import_empty_batches
from logs.logic.materialized_reports import sync_materialized_reports_for_import_batch
from logs.models import ManualDataUpload

logger = logging.getLogger(__name__)


def custom_import_preflight_check(mdu: ManualDataUpload):
    histograms, counts, dimensions = mdu.histograms_with_stats()
    months = {
        f"{k}-01": {"new": v, "this_month": None, "prev_year_avg": None, "prev_year_month": 0}
        for k, v in histograms["months"].items()
    }
    if len(histograms["organizations"]) <= 1:
        # Only a single organization is present
        # don't export organizations to preflight
        # organization is picked by the user
        organizations = None
    else:
        # TODO remove when we are going to display per organization data in preflight view
        organizations = {
            k: {
                "count": v["total"]["count"],
                "sum": v["total"]["sum"],
            }
            for k, v in histograms["organizations"].items()
        }

        resolved_organizations = dict(
            ManualDataUpload.organizations_from_data_cls(organizations.keys())
        )
        # fill in pks to organizations
        for name, org_data in organizations.items():
            organization = resolved_organizations[name]
            org_data['pk'] = organization and organization.pk
        # the following is not very nice, but we need the organizations data to be present
        # when doing related_months_data() below;
        # it is not stored to the database, just assigned to the object instance
        mdu.preflight['organizations'] = organizations

    # prepare month statistics
    related_months, used_metrics = mdu.related_months_data()

    for year_month, data in months.items():
        year, month, *_ = [int(e) for e in year_month.split('-')]
        last_year_month = f"{year - 1}-{month:02d}-01"
        last_year_months = {f"{year - 1}-{i:02d}-01" for i in range(1, 13)}
        data['this_month'] = related_months.get(year_month)

        # Display last year average only when all months contain data
        if last_year_months.issubset(related_months.keys()):
            data['prev_year_avg'] = {"sum": 0, "count": 0}
            for ymonth in last_year_months:
                data['prev_year_avg']['sum'] += related_months[ymonth]['sum']
                data['prev_year_avg']['count'] += related_months[ymonth]['count']
            data['prev_year_avg']['sum'] = round(data['prev_year_avg']['sum'] / 12)
            data['prev_year_avg']['count'] = round(data['prev_year_avg']['count'] / 12)
        else:
            data['prev_year_avg'] = None
        data['prev_year_month'] = related_months.get(last_year_month)

    return {
        'format_version': mdu.PREFLIGHT_FORMAT_VERSION,
        'celus_version': settings.CELUS_VERSION,
        'git_hash': settings.SENTRY_RELEASE,
        'generated': now().isoformat(),
        'log_count': counts["count"],
        'hits_total': counts["sum"],
        'months': months,
        'metrics': histograms["metrics"],
        'used_metrics': used_metrics,
        'title_count': len(histograms["titles"]),
        'organizations': organizations,
        'dimensions': dimensions,
    }


@atomic
def import_custom_data(
    mdu: ManualDataUpload,
    user: User,
    months: typing.Optional[typing.Iterable[str]] = None,
    empty=False,
) -> dict:
    """
    :param mdu:
    :param user:
    :param months: Can be used to limit which months of data will be loaded from the file -
                   see `import_counter_records` for more details how this works
    :param empty: If true import only empty import batches based od preflight["months"]
    :return: import statistics
    """
    stats = Counter()

    organizations = mdu.preflight.get("organizations", {"": {}}) or {"": {}}
    import_batches = []
    for org_name, org_data in organizations.items():

        records = mdu.data_to_records()
        if org_name:
            # Try to get organization
            try:
                organization = Organization.objects.get(pk=org_data.get("pk", 0))
            except Organization.DoesNotExist:
                raise OrganizationNotFound(org_name) from None

            # Filter records
            records = (e for e in records if e.organization == org_name)
        else:
            organization = mdu.organization

        if not mdu.check_organization_permissions(organization):
            raise OrganizationNotAllowedToImportRawData(organization)

        # TODO: the owner level should be derived from the user and the organization at hand
        if empty:
            new_ibs = import_empty_batches(
                mdu.report_type,
                organization,
                mdu.platform,
                months=list(mdu.preflight["months"].keys()),
                import_batch_kwargs={"user": user, "owner_level": mdu.owner_level},
            )
            new_stats = {}
        else:
            new_ibs, new_stats = import_counter_records(
                mdu.report_type,
                organization,
                mdu.platform,
                records,
                months=months,
                import_batch_kwargs={"user": user, "owner_level": mdu.owner_level},
            )

        import_batches.extend(new_ibs)
        stats.update(new_stats)

    mdu.import_batches.set(import_batches)
    mdu.mark_processed()  # this also saves the model

    for import_batch in import_batches:
        sync_materialized_reports_for_import_batch(import_batch)
    # the following could be used to debug the speed of this code chunk
    # from django.db import connection
    # qs = connection.queries
    # qs.sort(key=lambda x: -float(x['time']))
    # for q in qs[:3]:
    #     print(q['time'], q)
    return stats
