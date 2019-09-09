from modeltranslation.translator import translator, TranslationOptions
from .models import DimensionText, Metric, ReportType, Dimension, InterestGroup, \
    ReportInterestMetric, ReportDataView


class ReportTypeTranslationOptions(TranslationOptions):
    fields = ('name', 'desc')


class VirtualReportTypeTranslationOptions(TranslationOptions):
    fields = ('name', 'desc')


class InterestGroupTranslationOptions(TranslationOptions):
    fields = ('name',)


class MetricTranslationOptions(TranslationOptions):
    fields = ('name', 'desc')

class ReportInterestMetricTranslationOptions(TranslationOptions):
    fields = ('name',)


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
translator.register(ReportDataView, VirtualReportTypeTranslationOptions)
