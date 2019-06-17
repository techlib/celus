from modeltranslation.translator import translator, TranslationOptions
from .models import Organization


class OrganizationTranslationOptions(TranslationOptions):
    fields = ('name', 'short_name')


translator.register(Organization, OrganizationTranslationOptions)
