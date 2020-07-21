from django.contrib import admin

from .models import FooterImage, SiteLogo


@admin.register(FooterImage)
class FooterImageAdmin(admin.ModelAdmin):

    list_display = ('site', 'img', 'alt_text', 'position', 'last_modified')
    list_display_links = ('img',)


@admin.register(SiteLogo)
class FooterImageAdmin(admin.ModelAdmin):

    list_display = ('site', 'img', 'alt_text', 'last_modified')
    list_display_links = ('img',)
