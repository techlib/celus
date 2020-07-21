from django.contrib import admin

from .models import FooterImage, SiteLogo


@admin.register(FooterImage)
class FooterImageAdmin(admin.ModelAdmin):

    list_display = ('alt_text', 'site', 'img', 'position', 'last_modified')
    list_display_links = ('alt_text',)


@admin.register(SiteLogo)
class FooterImageAdmin(admin.ModelAdmin):

    list_display = ('alt_text', 'site', 'img', 'last_modified')
    list_display_links = ('alt_text',)
