from modeltranslation.translator import TranslationOptions, translator

from .models import Organization


class OrganizationTranslationOptions(TranslationOptions):
    fields = ('name', 'short_name')


translator.register(Organization, OrganizationTranslationOptions)
