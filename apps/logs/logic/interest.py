from logs.models import Dimension, DimensionText, InterestGroup, ReportType


def get_interest_type_dim_from_interest_rt(interest_rt: ReportType) -> Dimension:
    """
    Given an interest RT, it returns the dimension encoding the interest type.
    """
    return interest_rt.dimensions.get(short_name="Interest_Type")


def get_interest_subdim_ids_implying_availability(interest_rt: ReportType) -> [int]:
    """
    Give an interest RT, it returns values which when used to filter the data by interest type
    should give only those interest types which imply availability (not denials).
    """
    # names of interest groups that imply availability
    # remap the names to ids through the dimension text
    it_dim = get_interest_type_dim_from_interest_rt(interest_rt)
    return DimensionText.objects.filter(
        dimension=it_dim,
        text__in=(InterestGroup.objects.filter(implies_availability=True).values("short_name")),
    ).values_list("pk", flat=True)
