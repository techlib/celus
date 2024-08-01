from pyparsing import Word, alphanums, alphas, infix_notation, one_of, opAssoc
from rest_framework import serializers as s


def formula_parser():
    """
    Very simple parser for formulas inside report definitions. It supports the following operations
    which all work on matrices and produce a matrix as a result:

    - non-negative subtraction (jr1 - jr1goa) - works on cell level - if jr1goa is larger than jr1,
      zero is returned
    + addition (jr1 + jr1goa) - works on cell level
    | merge (jr1 | jr1goa) - works on row level - row from jr1goa is added only if row from jr1 is
      not present or has zero value
    () parenthesis for grouping
    """
    ident = Word(alphas, alphanums + "_")
    return infix_notation(
        ident, [(one_of("+ -"), 2, opAssoc.LEFT), ("|", 2, opAssoc.LEFT)], lpar="(", rpar=")"
    )


def parse_formula(formula):
    """
    Parse a formula and return a list of operations and operands.
    """
    try:
        return formula_parser().parse_string(formula).as_list()
    except Exception as e:
        raise s.ValidationError(f"Invalid formula: {e}") from e


class ReportDataSourceSerializer(s.Serializer):
    """
    If `name` is not present, it is taken from `reportType` or `id`.
    If `id` is not present, it is taken from `name`.
    So only `reportType` is required.
    """

    id = s.CharField(required=False)
    name = s.CharField(required=False)
    reportType = s.CharField()
    metric = s.CharField(allow_null=True)
    filters = s.DictField(required=False)
    fallbackFor = s.CharField(required=False)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if "name" not in attrs:
            attrs["name"] = attrs["reportType"] or attrs["id"]
        if "id" not in attrs:
            attrs["id"] = attrs["name"]
        return attrs


class ReportPartStageSerializer(s.Serializer):
    id = s.CharField(required=False)
    name = s.CharField()
    description = s.CharField(required=False)
    formula = s.CharField(validators=[parse_formula])

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if "id" not in attrs:
            attrs["id"] = attrs["name"]
        return attrs


class ReportPartSerializer(s.Serializer):
    name = s.CharField()
    description = s.CharField()
    explanation = s.CharField(required=False)
    stages = ReportPartStageSerializer(many=True)
    implementationNote = s.CharField(required=False)


class ReportSerializer(s.Serializer):
    name = s.CharField()
    description = s.CharField()
    parts = ReportPartSerializer(many=True)
    dataSources = ReportDataSourceSerializer(many=True)
    infoUrl = s.URLField(required=False)
