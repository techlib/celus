from modeltranslation.translator import TranslationOptions, translator

from .models import Platform


class PlatformTranslationOptions(TranslationOptions):
    fields = ('name', 'provider')


translator.register(Platform, PlatformTranslationOptions)
