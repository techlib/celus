from modeltranslation.translator import translator, TranslationOptions
from .models import Platform


class PlatformTranslationOptions(TranslationOptions):
    fields = ('name', 'short_name', 'provider')


translator.register(Platform, PlatformTranslationOptions)
