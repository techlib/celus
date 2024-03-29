from modeltranslation.translator import TranslationOptions, translator

from .models import (
    Dimension,
    DimensionText,
    InterestGroup,
    Metric,
    ReportInterestMetric,
    ReportType,
)


class ReportTypeTranslationOptions(TranslationOptions):
    fields = ('name', 'desc')


class InterestGroupTranslationOptions(TranslationOptions):
    fields = ('name',)


class MetricTranslationOptions(TranslationOptions):
    fields = ('name', 'desc')


class ReportInterestMetricTranslationOptions(TranslationOptions):
    fields = ()


class DimensionTextTranslationOptions(TranslationOptions):
    fields = ('text_local',)


class DimensionTranslationOptions(TranslationOptions):
    fields = ('name', 'desc')


translator.register(ReportType, ReportTypeTranslationOptions)
translator.register(Dimension, DimensionTranslationOptions)
translator.register(DimensionText, DimensionTextTranslationOptions)
translator.register(InterestGroup, InterestGroupTranslationOptions)
translator.register(Metric, MetricTranslationOptions)
translator.register(ReportInterestMetric, ReportInterestMetricTranslationOptions)
