from modeltranslation.translator import translator, TranslationOptions
from .models import LogType


class LogTypeTranslationOptions(TranslationOptions):
    fields = ('name', 'desc')


translator.register(LogType, LogTypeTranslationOptions)
