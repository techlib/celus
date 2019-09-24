from django.contrib import admin
from modeltranslation.admin import TranslationAdmin

from .models import Annotation


@admin.register(Annotation)
class AnnotationAdmin(TranslationAdmin):

    list_display = ['subject', 'start_date', 'end_date', 'organization', 'platform', 'report_type',
                    'title', 'author']
    search_fields = ['subject', 'short_message', 'message', 'organization__short_name',
                     'platform__short_name', 'title__name', 'report_type__short_name']
    list_filter = ['platform', 'organization', 'author']
    readonly_fields = ['title']
