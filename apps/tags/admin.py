from typing import Union

from django.contrib import admin
from django.utils.html import format_html

from . import models


class TagPreviewMixin:
    @admin.display(description='Preview')
    def rendered(self, obj: Union[models.Tag, models.TagClass]):
        return format_html(
            f"<span style='padding: 4px 8px; background-color: {obj.bg_color}; "
            f"color: {obj.text_color}; border-radius: 16px'>{{}}</span>",
            obj.name,
        )


@admin.register(models.Tag)
class TagAdmin(TagPreviewMixin, admin.ModelAdmin):

    list_display = [
        'pk',
        'name',
        'tag_class',
        'text_color',
        'bg_color',
        'can_see',
        'can_assign',
        'rendered',
    ]
    readonly_fields = ['last_updated_by']
    search_fields = ['name', 'tag_class__name', 'text_color', 'bg_color']


@admin.register(models.TagClass)
class TagClassAdmin(TagPreviewMixin, admin.ModelAdmin):

    list_display = ['pk', 'name', 'text_color', 'bg_color', 'can_create_tags', 'rendered']
    readonly_fields = ['last_updated_by']
    search_fields = ['name', 'text_color', 'bg_color']


@admin.register(models.TaggingBatch)
class TaggingBatchAdmin(admin.ModelAdmin):

    list_display = ['pk', 'state', 'created', 'last_updated_by', 'tag', 'tag_class']
    list_filter = ['state', 'last_updated_by', 'tag', 'tag_class']
