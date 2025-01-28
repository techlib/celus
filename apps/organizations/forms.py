from dal import autocomplete
from django import forms

from .models import Organization


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = "__all__"  # noqa
        widgets = {
            "country": autocomplete.Select2(url="country-autocomplete"),
            "state": autocomplete.Select2(url="state-autocomplete", forward=["country"]),
        }

    def save(self, *args, **kwargs):
        # Make sure that empty values are stored for instance as well
        # for autocomplete fields
        self.instance.country = self.cleaned_data.get("country", "")
        self.instance.state = self.cleaned_data.get("state", "")
        return super().save(*args, **kwargs)
