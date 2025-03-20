import logging
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from logs.models import InterestGroup, InterestProfile, ReportType
logger = logging.getLogger(__name__)

INTEREST_DEFAULT_PROFILES = [
    {
        "short_name": "unique",
        "name": "Unique",
        "default": False,
        "description": "Interest profile using Unique metrics",
    },
    {
        "short_name": "total",
        "name": "Total",
        "default": True,
        "description": "Interest profile using Total metrics",
    },
]

INTEREST_DEFAULT_GROUPS = [
    {
        "short_name": "full_text",
        "name_en": "Full Text",
        "name_cs": "Plný text",
        "implies_availability": True,
        "important": True,
    },
    {
        "short_name": "search",
        "name_en": "Search",
        "name_cs": "Hledání",
        "implies_availability": True,
        "important": True,
    },
    {
        "short_name": "multimedia",
        "name_en": "Multimedia",
        "name_cs": "Multimédia",
        "implies_availability": True,
        "important": True,
    },
    # denial metrics
    {
        "short_name": "full_text_denial",
        "name_en": "Denial - full text",
        "name_cs": "Odmítnutí - plný text",
        "implies_availability": False,
    },
    {
        "short_name": "search_denial",
        "name_en": "Denial - search",
        "name_cs": "Odmítnutí - hledání",
        "implies_availability": False,
    },
    # other metrics
    {"short_name": "other", "name_en": "Other", "name_cs": "Jiné", "implies_availability": True},
]

C51_MULTIMEDIA_DATA_TYPES = ["Audiovisual", "Image", "Interactive_Resource", "Multimedia", "Sound"]

C51_MAPPINGS = {
    "Access_Type": {
        "dimension": "Access_Type",
        "default": "Controlled",
        "values": {"Free": ["Free_To_Read", "Open"]},
    },
    "Access_Method": {
        "dimension": "Access_Method",
        "default": "Normal",
        "values": {"TDM": ["TDM"]},
    },
}

C50_MAPPINGS = {
    "Access_Type": {
        "dimension": "Access_Type",
        "default": "Controlled",
        "values": {"Free": ["OA_Gold", "OA_Delayed", "Other_Free_to_Read"]},
    },
    "Access_Method": {
        "dimension": "Access_Method",
        "default": "Normal",
        "values": {"TDM": ["TDM"]},
    },
}

# `auto` is True if the dimension is automatically created by the system
# using interest computation code logic.
# `default_value` is the value that is used if the report itself does not define
# how the dimension should be extracted (using `mappings` in `INTEREST_DEFAULT_REPORT_TYPES`).
DEFAULT_INTEREST_DIMENSIONS = [
    {"name": "Original Report Type", "short_name": "Original_Report_Type", "auto": True},
    {"name": "Original Metric", "short_name": "Original_Metric", "auto": True},
    {
        "name": "Access Type",
        "short_name": "Access_Type",
        "auto": False,
        "default_value": "Controlled",
    },
    {
        "name": "Access Method",
        "short_name": "Access_Method",
        "auto": False,
        "default_value": "Normal",
    },
]

INTEREST_EXTRA_DIMENSIONS = [d["short_name"] for d in DEFAULT_INTEREST_DIMENSIONS if not d["auto"]]


INTEREST_DEFAULT_REPORT_TYPES = {
    (51, "IR"): {
        "interest": {
            "full_text": {
                "metrics": {"Total_Item_Requests": "total", "Unique_Item_Requests": "unique"},
                "filters": [
                    {"dimension": "Data_Type", "values": C51_MULTIMEDIA_DATA_TYPES, "negate": True}
                ],
            },
            # Multimedia interest uses the same metric as the full_text interest, and only differs
            # in the filter applied to it.
            "multimedia": {
                "metrics": {"Total_Item_Requests": "total", "Unique_Item_Requests": "unique"},
                "filters": [{"dimension": "Data_Type", "values": C51_MULTIMEDIA_DATA_TYPES}],
            },
            "full_text_denial": {
                "metrics": {"No_License": None, "Limit_Exceeded": None},
                "filters": [
                    {"dimension": "Data_Type", "values": C51_MULTIMEDIA_DATA_TYPES, "negate": True}
                ],
            },
        },
        "mappings": C51_MAPPINGS,
    },
    (51, "TR"): {
        "interest": {
            "full_text": {
                "metrics": {"Total_Item_Requests": "total", "Unique_Item_Requests": "unique"}
            },
            "full_text_denial": {"metrics": {"No_License": None, "Limit_Exceeded": None}},
        },
        "mappings": C51_MAPPINGS,
        "superseded_by": (51, "IR"),
    },
    (51, "DR"): {
        "interest": {
            "search": {"metrics": {"Searches_Regular": None}},
            "search_denial": {"metrics": {"No_License": None, "Limit_Exceeded": None}},
        },
        "mappings": {"Access_Method": C51_MAPPINGS["Access_Method"]},  # Access_Type is not used
    },
    (51, "PR"): {},  # no interest for PR, this ensures deletion of obsolete RIMs
    # The following is a sketch of how PR interest could be computed. But because it is superseded
    # by both TR and DR, it would need a change to the whole interest computation code.
    # Because the value of PR is very low, we will not implement it. At least not for now.
    #     "interest": {
    #         "full_text": {
    #             "metrics": {"Total_Item_Requests": "total", "Unique_Item_Requests": "unique"},
    #             "filters": [
    #                 {"dimension": "Data_Type",
    #                  "values": C51_MULTIMEDIA_DATA_TYPES,
    #                  "negate": True}
    #             ],
    #         },
    #         "full_text_denial": {"metrics": {"No_License": None, "Limit_Exceeded": None}},
    #         "search": {"metrics": {"Searches_Regular": None}},
    #         "search_denial": {"metrics": {"No_License": None, "Limit_Exceeded": None}},
    #         "multimedia": {
    #             "metrics": {"Total_Item_Requests": "total", "Unique_Item_Requests": "unique"},
    #             "filters": [{"dimension": "Data_Type", "values": C51_MULTIMEDIA_DATA_TYPES}],
    #         },
    #     },
    #     "mappings": C51_MAPPINGS,
    #     "superseded_by": (51, "TR"),
    # },
    # IR from C5.0 will not be used as the data are usually messy and do not match the corresponding
    # TR reports. The definition of IR is much better in 5.1, so we will start supporting it from
    # 5.1 onwards.
    # (5, "IR"): {
    #     "interest": {
    #         "full_text": {
    #             "metrics": {"Total_Item_Requests": "total", "Unique_Item_Requests": "unique"},
    #             "filters": [{"dimension": "Data_Type", "values": ["Multimedia"], "negate": True}],
    #         },
    #         # Multimedia interest uses the same metric as the full_text interest, and only differs
    #         # in the filter applied to it.
    #         # Because we do not support filters in the interest computation yet, we cannot use it.
    #         # Thus, multimedia interest is not computed from IR and IR_M1 has to be used
    #         #
    #         # "multimedia": {
    #         #     "metrics": ["Total_Item_Requests"],
    #         #     "filters": [{"dimension": "Data_Type", "values": ["Multimedia"]}],
    #         # },
    #         "full_text_denial": {
    #             "metrics": {"No_License": None, "Limit_Exceeded": None},
    #             "filters": [{"dimension": "Data_Type", "values": ["Multimedia"], "negate": True}],
    #         },
    #     },
    #     "superseded_by": (51, "IR"),
    # },
    (5, "TR"): {
        "interest": {
            "full_text": {
                "metrics": {"Total_Item_Requests": "total", "Unique_Item_Requests": "unique"}
            },
            "full_text_denial": {"metrics": {"No_License": None, "Limit_Exceeded": None}},
        },
        # TR is superseded by both C51_TR and C5_IR, but we cannot express it right now,
        # it will have to wait for the new interest computation
        # for now, we use the C51_TR, because this will be used in production
        "superseded_by": (51, "TR"),
        "mappings": C50_MAPPINGS,
    },
    (5, "IR_M1"): {
        "interest": {
            "multimedia": {
                "metrics": {"Total_Item_Requests": "total", "Unique_Item_Requests": "unique"}
            }
        },
        "superseded_by": (51, "IR"),
    },
    (5, "DR"): {
        "interest": {
            "search": {"metrics": {"Searches_Regular": None}},
            "search_denial": {"metrics": {"No_License": None, "Limit_Exceeded": None}},
        },
        "superseded_by": (51, "DR"),
        "mappings": {"Access_Method": C50_MAPPINGS["Access_Method"]},  # Access_Type is not used
    },
    (5, "PR"): {},  # no interest for PR, this ensures deletion of obsolete RIMs
    (4, "JR1"): {
        "interest": {"full_text": {"metrics": {"FT Article Requests": None}}},
        "superseded_by": (5, "TR"),
    },
    (4, "BR2"): {
        "interest": {"full_text": {"metrics": {"Book Section Requests": None}}},
        "superseded_by": (5, "TR"),
    },
    (4, "DB1"): {
        "interest": {"search": {"metrics": {"Regular Searches": None}}},
        "superseded_by": (5, "DR"),
    },
}


def create_interest_rt() -> "ReportType":
    from logs.models import Dimension, ReportType, ReportTypeToDimension

    interest_rt = ReportType.objects.get_interest_rt()
    if not interest_rt:
        interest_rt = ReportType.objects.create(short_name="interest", name="Interest")
    for i, ddef in enumerate(DEFAULT_INTEREST_DIMENSIONS):
        dim = Dimension.objects.get_or_create(
            short_name=ddef["short_name"], defaults={"name": ddef["name"]}
        )[0]
        if (
            existing := interest_rt.reporttypetodimension_set.filter(position=i).first()
        ) and existing.dimension != dim:
            logger.info("Position #%d is occupied by %s, removing it", i, existing)
            existing.delete()
        ReportTypeToDimension.objects.get_or_create(
            report_type=interest_rt, dimension=dim, position=i
        )
    create_default_interest_dimension_value_mappings(interest_rt)
    return interest_rt


def create_default_interest_dimension_value_mappings(interest_rt: "ReportType") -> None:
    from logs.models import Dimension, InterestDimensionValueMapping

    for ddef in DEFAULT_INTEREST_DIMENSIONS:
        dim = Dimension.objects.get_or_create(
            short_name=ddef["short_name"], defaults={"name": ddef["name"]}
        )[0]
        if not ddef.get("auto"):
            # auto is computed in the code, so it does not need default value
            InterestDimensionValueMapping.objects.get_or_create(
                interest_rtdim=interest_rt.reporttypetodimension_set.get(dimension=dim),
                source_rtdim=None,
                defaults={"default_value": ddef.get("default_value")},
            )


def create_default_profiles() -> List["InterestProfile"]:
    from logs.models import InterestConfig, InterestProfile

    profiles = []
    for pdef in INTEREST_DEFAULT_PROFILES:
        profile, created = InterestProfile.objects.get_or_create(
            short_name=pdef["short_name"],
            defaults={"name": pdef["name"], "desc": pdef["description"]},
        )
        if created:
            logger.info("Created interest profile %s", profile)
        if pdef["default"]:
            _ic, created = InterestConfig.objects.get_or_create(
                organization=None, interest_profile=profile
            )
            if created:
                logger.info("Created default interest config")
        profiles.append(profile)
    return profiles


def create_default_interest_groups() -> List["InterestGroup"]:
    from logs.models import InterestGroup, Metric

    groups = []
    for i, igdef in enumerate(INTEREST_DEFAULT_GROUPS):
        # ensure the metric exists
        metric, _created = Metric.objects.get_or_create(
            short_name=igdef["short_name"],
            defaults={"name_en": igdef["name_en"], "name_cs": igdef["name_cs"]},
        )
        ig, created = InterestGroup.objects.get_or_create(
            short_name=igdef["short_name"],
            defaults={
                "name_en": igdef["name_en"],
                "name_cs": igdef["name_cs"],
                "implies_availability": igdef.get("implies_availability", False),
                "important": igdef.get("important", False),
                "metric": metric,
                "position": i,
            },
        )
        if created:
            logger.info("Created interest group %s", ig)
        groups.append(ig)
    return groups
