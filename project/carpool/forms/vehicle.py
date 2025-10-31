from django import forms
from django.conf import settings
from carpool.models import Vehicle


class VehicleForm(forms.ModelForm):
    seats = forms.IntegerField(
        required=True,
        min_value=1,
        max_value=settings.MAXIMUM_SEATS_IN_VEHICLE,
    )

    class Meta:
        model = Vehicle
        fields = ["name", "description", "seats", "geqCO2_per_km"]
