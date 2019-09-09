from modeltranslation.translator import translator, TranslationOptions

from .models import ReportDataView


class ReportDataViewTranslationOptions(TranslationOptions):
    fields = ('name', 'desc')


translator.register(ReportDataView, ReportDataViewTranslationOptions)
