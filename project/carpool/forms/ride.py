import datetime

from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.gis.geos import GEOSGeometry

from carpool.models.ride import Ride
from carpool.models import Step, Vehicle
from carpool.mixins import BaseLocationMixin
from carpool.utils import get_or_create_location
from carpool.forms.location import LocationForm

from django.conf import settings


# Formset to handle multiple stopovers locations in a ride
StopOverFormSet = forms.formset_factory(
    LocationForm,
    min_num=0,
    extra=0,
    max_num=settings.MAXIMUM_STEPOVERS_IN_RIDE,
)


class EditRideForm(forms.ModelForm):
    duration = forms.FloatField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Ride
        fields = [
            "geometry",
            "duration",
            "start_dt",
            "price",
            "comment",
            "payment_method",
            "seats_offered",
        ]
        widgets = {
            "geometry": forms.HiddenInput(),
            "duration": forms.HiddenInput(),
            "start_dt": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "min": timezone.now().strftime("%Y-%m-%dT%H:%M"),
                    "max": (timezone.now() + datetime.timedelta(days=365)).strftime("%Y-%m-%dT%H:%M"),
                }
            ),
            "comment": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        instance = kwargs.get("instance", None)

        # Set initial value for geometry field
        if instance and instance.geometry:
            if "initial" not in kwargs:
                kwargs["initial"] = {}
            kwargs["initial"]["geometry"] = instance.geometry.geojson

        # Set initial value for start_dt field
        if instance and instance.start_dt:
            if "initial" not in kwargs:
                kwargs["initial"] = {}
            kwargs["initial"]["start_dt"] = timezone.localtime(
                instance.start_dt
            ).strftime("%Y-%m-%dT%H:%M")

        # Set duration field initial value in hours
        if instance and instance.duration:
            if "initial" not in kwargs:
                kwargs["initial"] = {}
            kwargs["initial"]["duration"] = instance.duration.total_seconds() / 3600

        # Add form-control class to all fields
        for field_name, field in self.base_fields.items():
            widget = field.widget
            if field_name == "payment_method":
                continue
            _css_class = widget.attrs.get("class", "")
            widget.attrs.setdefault("class", "form-control")

        super().__init__(*args, **kwargs)

        # If data is provided, bind sub-forms to it; otherwise, use instance data
        if self.data:
            self.departure = LocationForm(self.data, prefix="departure")
            self.arrival = LocationForm(self.data, prefix="arrival")
            self.stopovers = StopOverFormSet(self.data, prefix="stopovers")
        else:
            if self.instance:
                self.departure = LocationForm(
                    initial={
                        "fulltext": kwargs["instance"].start_loc.fulltext,
                        "street": kwargs["instance"].start_loc.street,
                        "zipcode": kwargs["instance"].start_loc.zipcode,
                        "city": kwargs["instance"].start_loc.city,
                        "latitude": kwargs["instance"].start_loc.lat,
                        "longitude": kwargs["instance"].start_loc.lng,
                    },
                    prefix="departure",
                )
                self.arrival = LocationForm(
                    initial={
                        "fulltext": kwargs["instance"].end_loc.fulltext,
                        "street": kwargs["instance"].end_loc.street,
                        "zipcode": kwargs["instance"].end_loc.zipcode,
                        "city": kwargs["instance"].end_loc.city,
                        "latitude": kwargs["instance"].end_loc.lat,
                        "longitude": kwargs["instance"].end_loc.lng,
                    },
                    prefix="arrival",
                )
                self.stopovers = StopOverFormSet(
                    initial=[
                        {
                            "fulltext": s.location.fulltext,
                            "street": s.location.street,
                            "zipcode": s.location.zipcode,
                            "city": s.location.city,
                            "latitude": s.location.lat,
                            "longitude": s.location.lng,
                        }
                        for s in kwargs["instance"].steps.all()
                    ],
                    prefix="stopovers",
                )
            else:
                self.departure = LocationForm(prefix="departure")
                self.arrival = LocationForm(prefix="arrival")
                self.stopovers = StopOverFormSet(prefix="stopovers")

        self.fields["geometry"].initial = (
            self.instance.geometry.geojson if self.instance.geometry else ""
        )
        now = timezone.now().strftime("%Y-%m-%dT%H:%M")
        self.fields["start_dt"].widget.attrs["min"] = now
        one_year_from_now = (timezone.now() + datetime.timedelta(days=365)).strftime("%Y-%m-%dT%H:%M")
        self.fields["start_dt"].widget.attrs["max"] = one_year_from_now

    def clean_duration(self):
        hours = self.cleaned_data.get("duration")
        if hours in (None, ""):
            return None
        try:
            return datetime.timedelta(hours=float(hours))
        except (TypeError, ValueError):
            raise forms.ValidationError("Enter duration in hours as a number.")

    def clean_geometry(self):
        data = self.cleaned_data["geometry"]
        if isinstance(data, str):
            return GEOSGeometry(data)
        return data

    def clean_start_dt(self):
        data = self.cleaned_data["start_dt"]
        if data < timezone.now():
            self.add_error("start_dt", _("Departure date cannot be in the past."))
        if data > timezone.now() + datetime.timedelta(days=365):
            self.add_error("start_dt", _("Departure date cannot be more than one year in the future."))
        return data

    def is_valid(self):
        valid = super().is_valid()
        dep_valid = self.departure.is_valid()
        arr_valid = self.arrival.is_valid()
        return valid and dep_valid and arr_valid

    def save(self, ride):
        # Update or create departure location
        d_data = self.departure.cleaned_data
        departure = get_or_create_location(d_data)
        ride.start_loc = departure

        # Update or create arrival location
        a_data = self.arrival.cleaned_data
        arrival = get_or_create_location(a_data)
        ride.end_loc = arrival

        # Stopovers handling
        ride.steps.clear()
        for index, so_form in enumerate(self.stopovers.cleaned_data):
            so_location = get_or_create_location(so_form)
            step = Step.objects.create(order=index + 1, location=so_location)
            ride.steps.add(step)

        # Update ride fields
        ride.geometry = self.cleaned_data["geometry"]
        ride.duration = self.cleaned_data["duration"]
        ride.start_dt = self.cleaned_data["start_dt"]
        ride.end_dt = ride.start_dt + ride.duration
        ride.price = self.cleaned_data["price"]
        ride.comment = self.cleaned_data["comment"]
        ride.payment_method = self.cleaned_data["payment_method"]
        ride.seats_offered = self.cleaned_data["seats_offered"]

        ride.save()
        return ride


class CreateRideStep1Form(forms.Form):
    r_geometry = forms.CharField(required=True, widget=forms.HiddenInput())
    r_duration = forms.FloatField(required=True, widget=forms.HiddenInput())
    payment_method = forms.MultipleChoiceField(
        required=False,
        choices=Ride.PaymentMethod.choices,
        widget=forms.CheckboxSelectMultiple,
    )
    departure_datetime = forms.DateTimeField(
        required=True,
        widget=forms.DateTimeInput(
            attrs={
                "type": "datetime-local",
                "class": "form-control",
                "min": timezone.now().strftime("%Y-%m-%dT%H:%M"),
                "max": (timezone.now() + datetime.timedelta(days=365)).strftime("%Y-%m-%dT%H:%M"),
            },
        ),
    )

    def is_valid(self):
        valid = super().is_valid()
        dep_valid = self.departure.is_valid()
        arr_valid = self.arrival.is_valid()
        so_valid = self.stopovers.is_valid()
        return valid and dep_valid and arr_valid and so_valid

    def clean(self):
        cleaned_data = super().clean()

        if not (hasattr(self, "departure") and self.departure.is_valid()):
            return cleaned_data
        if not (hasattr(self, "arrival") and self.arrival.is_valid()):
            return cleaned_data

        # Prevent creating a ride where departure and arrival are identical
        loc1 = self.departure.cleaned_data
        loc2 = self.arrival.cleaned_data

        if BaseLocationMixin.location_are_identical(loc1, loc2):
            self.add_error(
                None,
                _("Departure and arrival locations cannot be the same."),
            )

        if "departure_datetime" in cleaned_data:
            data = cleaned_data["departure_datetime"]
            # check if too late or before now
            if data < timezone.now():
                self.add_error("departure_datetime", _("Departure date cannot be in the past."))
            elif data > timezone.now() + datetime.timedelta(days=365):
                self.add_error(
                    "departure_datetime",
                    _("Departure date cannot be more than one year in the future."),
                )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Departure, arrival and stopovers forms
        if self.data:
            self.departure = LocationForm(self.data, prefix="departure")
            self.arrival = LocationForm(self.data, prefix="arrival")
            self.stopovers = StopOverFormSet(self.data, prefix="stopovers")
        else:
            self.departure = LocationForm(prefix="departure")
            self.arrival = LocationForm(prefix="arrival")
            self.stopovers = StopOverFormSet(prefix="stopovers")

        for field_name, field in self.fields.items():
            widget = field.widget
            css_class = widget.attrs.get("class", "")
            if self.errors.get(field_name):
                widget.attrs["class"] = f"{css_class} is-invalid"
            else:
                widget.attrs.setdefault("class", "form-control")

        now = timezone.now().strftime("%Y-%m-%dT%H:%M")
        self.fields["departure_datetime"].widget.attrs["min"] = now
        one_year_from_now = (timezone.now() + datetime.timedelta(days=365)).strftime("%Y-%m-%dT%H:%M")
        self.fields["departure_datetime"].widget.attrs["max"] = one_year_from_now


class CreateRideStep2Form(forms.Form):
    seats_offered = forms.IntegerField(
        required=True,
        min_value=1,
        max_value=settings.MAXIMUM_SEATS_IN_VEHICLE,
        widget=forms.NumberInput(
            attrs={
                "placeholder": _("Number of seats available for the carpool"),
                "class": "form-control",
            },
        ),
        help_text=_("Number of seats available for the carpool."),
    )

    vehicle = forms.ModelChoiceField(
        required=True,
        queryset=Vehicle.objects.all(),
        widget=forms.Select(
            attrs={
                "class": "form-control",
            },
        ),
        help_text=_("Select the vehicle you will use for this ride."),
        label=_("Vehicle"),
    )

    price = forms.DecimalField(
        required=True,
        min_value=0,
        decimal_places=2,
        max_value=999,
        widget=forms.NumberInput(
            attrs={
                "placeholder": _("Price per seat"),
                "class": "form-control",
            },
        ),
    )

    payment_method = forms.MultipleChoiceField(
        required=False,
        choices=Ride.PaymentMethod.choices,
        widget=forms.CheckboxSelectMultiple,
    )

    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
            },
        ),
        label=_("Comment (optional)"),
    )

    def clean(self):
        # Need to check here that seats_offered is not greater than vehicle.seats
        # since we use a forms.Form instead of a forms.ModelForm, we don't have access to
        # self.instance and call the model's clean() method.

        # TODO: Maybe we need to refactor this in the future by using a ModelForm here.

        cleaned_data = super().clean()
        vehicle = cleaned_data.get("vehicle")
        seats = cleaned_data.get("seats_offered")

        if vehicle and seats and seats > vehicle.seats:
            self.add_error(
                "seats_offered",
                _("Seats offered cannot be greater than vehicle seats."),
            )
        return cleaned_data
