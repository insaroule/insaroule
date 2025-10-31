from django import forms
from django.utils.translation import gettext_lazy as _


class LocationForm(forms.Form):
    """Form to capture location details."""

    fulltext = forms.CharField(widget=forms.HiddenInput(), required=True)
    street = forms.CharField(widget=forms.HiddenInput(), required=False)
    zipcode = forms.CharField(widget=forms.HiddenInput(), required=True)
    city = forms.CharField(widget=forms.HiddenInput(), required=True)
    latitude = forms.FloatField(widget=forms.HiddenInput(), required=True)
    longitude = forms.FloatField(widget=forms.HiddenInput(), required=True)

    def clean_latitude(self):
        latitude = self.cleaned_data.get("latitude")
        if latitude < -90 or latitude > 90:
            raise forms.ValidationError(_("Latitude must be between -90 and 90."))
        return latitude

    def clean_longitude(self):
        longitude = self.cleaned_data.get("longitude")
        if longitude < -180 or longitude > 180:
            raise forms.ValidationError(_("Longitude must be between -180 and 180."))
        return longitude
