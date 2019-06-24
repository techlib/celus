from modeltranslation.translator import translator, TranslationOptions
from .models import DimensionText, Metric, ReportType, Dimension


class ReportTypeTranslationOptions(TranslationOptions):
    fields = ('name', 'desc')


class MetricTranslationOptions(TranslationOptions):
    fields = ('name', 'desc')


class DimensionTextTranslationOptions(TranslationOptions):
    fields = ('text_local',)


class DimensionTranslationOptions(TranslationOptions):
    fields = ('name', 'desc')


translator.register(ReportType, ReportTypeTranslationOptions)
translator.register(Dimension, DimensionTranslationOptions)
translator.register(DimensionText, DimensionTextTranslationOptions)
translator.register(Metric, MetricTranslationOptions)

