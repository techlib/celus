from django.views.generic import TemplateView


class RedocView(TemplateView):
    template_name = "api/redoc.html"
