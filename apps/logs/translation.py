from modeltranslation.translator import translator, TranslationOptions
from .models import DimensionText, Metric, ReportType, Dimension, InterestGroup


class ReportTypeTranslationOptions(TranslationOptions):
    fields = ('name', 'desc')


class InterestGroupTranslationOptions(TranslationOptions):
    fields = ('name',)


class MetricTranslationOptions(TranslationOptions):
    fields = ('name', 'desc', 'name_in_interest_group')


class DimensionTextTranslationOptions(TranslationOptions):
    fields = ('text_local',)


class DimensionTranslationOptions(TranslationOptions):
    fields = ('name', 'desc')


translator.register(ReportType, ReportTypeTranslationOptions)
translator.register(Dimension, DimensionTranslationOptions)
translator.register(DimensionText, DimensionTextTranslationOptions)
translator.register(InterestGroup, InterestGroupTranslationOptions)
translator.register(Metric, MetricTranslationOptions)

