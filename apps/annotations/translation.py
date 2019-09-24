from modeltranslation.translator import translator, TranslationOptions
from .models import Annotation


class AnnotationTranslationOptions(TranslationOptions):
    fields = ('subject', 'short_message', 'message')


translator.register(Annotation, AnnotationTranslationOptions)
