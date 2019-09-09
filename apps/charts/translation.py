from modeltranslation.translator import translator, TranslationOptions

from charts.models import ChartDefinition
from .models import ReportDataView


class ReportDataViewTranslationOptions(TranslationOptions):
    fields = ('name', 'desc')


class ChartDefinitionTranslationOptions(TranslationOptions):
    fields = ('name', 'desc')


translator.register(ReportDataView, ReportDataViewTranslationOptions)
translator.register(ChartDefinition, ChartDefinitionTranslationOptions)
