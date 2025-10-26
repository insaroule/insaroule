import datetime

from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.gis.geos import GEOSGeometry

from carpool.models.ride import Ride
from carpool.models import Vehicle


MAXIMUM_SEATS_IN_VEHICLE = 8


class VehicleForm(forms.ModelForm):
    seats = forms.IntegerField(
        required=True,
        min_value=1,
        max_value=MAXIMUM_SEATS_IN_VEHICLE,
    )
    geqCO2_per_km = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(
            attrs={
                "placeholder": "",
                "class": "form-control",
            }
        ),
        help_text=(
            "Number of grams of CO2 emitted per kilometer. Leave empty if unknown."
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If the instance has geqCO2_per_km set to None, show an empty string
        instance = getattr(self, "instance", None)
        if instance is not None and getattr(instance, "geqCO2_per_km", None) is None:
            # set initial to empty string so widget doesn't render 'None'
            self.fields["geqCO2_per_km"].initial = ""

    def clean_geqCO2_per_km(self):
        """Convert empty string to None so the model receives a true NULL when unknown."""
        val = self.cleaned_data.get("geqCO2_per_km")
        if val in ("", None):
            return None
        return val

    class Meta:
        model = Vehicle
        fields = ["name", "description", "seats", "geqCO2_per_km"]


class CreateRideForm(forms.Form):
    # Departure information
    d_fulltext = forms.CharField(required=True, widget=forms.HiddenInput())
    d_street = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )  # Not necessary a street (could be a city)
    d_zipcode = forms.CharField(required=True, widget=forms.HiddenInput())
    d_city = forms.CharField(required=True, widget=forms.HiddenInput())
    d_latitude = forms.FloatField(required=True, widget=forms.HiddenInput())
    d_longitude = forms.FloatField(required=True, widget=forms.HiddenInput())

    # Arrival information
    a_fulltext = forms.CharField(required=True, widget=forms.HiddenInput())
    a_street = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )  # Not necessary a street (could be a city)
    a_zipcode = forms.CharField(required=True, widget=forms.HiddenInput())
    a_city = forms.CharField(required=True, widget=forms.HiddenInput())
    a_latitude = forms.FloatField(required=True, widget=forms.HiddenInput())
    a_longitude = forms.FloatField(required=True, widget=forms.HiddenInput())

    # Routing information
    r_geometry = forms.CharField(required=True, widget=forms.HiddenInput())
    r_duration = forms.FloatField(required=True, widget=forms.HiddenInput())

    departure_datetime = forms.DateTimeField(
        required=True,
        widget=forms.DateTimeInput(
            attrs={
                "type": "datetime-local",
                "class": "form-control",
                "min": timezone.now().strftime("%Y-%m-%dT%H:%M"),
            },
        ),
    )

    seats_offered = forms.IntegerField(
        required=True,
        min_value=1,
        max_value=MAXIMUM_SEATS_IN_VEHICLE,
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

    price_per_seat = forms.DecimalField(
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
        cleaned_data = super().clean()
        # Prevent creating a ride where departure and arrival are identical
        d_lat = cleaned_data.get("d_latitude")
        d_lng = cleaned_data.get("d_longitude")
        a_lat = cleaned_data.get("a_latitude")
        a_lng = cleaned_data.get("a_longitude")

        # Use a small tolerance for float comparisons
        if (d_lat is not None and a_lat is not None
            and d_lng is not None and a_lng is not None
            and abs(d_lat - a_lat) < 1e-5
            and abs(d_lng - a_lng) < 1e-5):
            self.add_error(
                "a_fulltext",
                _("Departure and arrival locations cannot be the same."),
            )
        price = cleaned_data.get("price_per_seat")
        payment = cleaned_data.get("payment_method")

        if seats_offered := cleaned_data.get("seats_offered"):
            vehicle = cleaned_data.get("vehicle")
            if vehicle and seats_offered > vehicle.seats:
                self.add_error(
                    "seats_offered",
                    _(
                        "The number of seats offered (%(offered)s) cannot exceed the number of seats in the vehicle (%(vehicle)s)."
                    )
                    % {"offered": seats_offered, "vehicle": vehicle.seats},
                )

        if price is not None and price > 0:
            if not payment:
                self.add_error(
                    "payment_method",
                    _("A payment method is required if a price is set."),
                )

        if price is not None and price > 999:
            self.add_error(
                "price_per_seat",
                _("The price per seat seems unreasonably high."),
            )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget
            if field_name == "payment_method":
                if self.errors.get(field_name):
                    widget.attrs["class"] = "is-invalid"
                continue
            css_class = widget.attrs.get("class", "")
            if self.errors.get(field_name):
                widget.attrs["class"] = f"{css_class} is-invalid"
            else:
                widget.attrs.setdefault("class", "form-control")

        now = timezone.now().strftime("%Y-%m-%dT%H:%M")
        self.fields["departure_datetime"].widget.attrs["min"] = now


class EditRideForm(forms.Form):
    # Departure information
    d_fulltext = forms.CharField(required=True, widget=forms.HiddenInput())
    d_street = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )  # Not necessary a street (could be a city)
    d_zipcode = forms.CharField(required=True, widget=forms.HiddenInput())
    d_city = forms.CharField(required=True, widget=forms.HiddenInput())
    d_latitude = forms.FloatField(required=True, widget=forms.HiddenInput())
    d_longitude = forms.FloatField(required=True, widget=forms.HiddenInput())

    # Arrival information
    a_fulltext = forms.CharField(required=True, widget=forms.HiddenInput())
    a_street = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )  # Not necessary a street (could be a city)
    a_zipcode = forms.CharField(required=True, widget=forms.HiddenInput())
    a_city = forms.CharField(required=True, widget=forms.HiddenInput())
    a_latitude = forms.FloatField(required=True, widget=forms.HiddenInput())
    a_longitude = forms.FloatField(required=True, widget=forms.HiddenInput())

    # Routing information
    r_geometry = forms.CharField(required=True, widget=forms.HiddenInput())
    r_duration = forms.FloatField(required=True, widget=forms.HiddenInput())

    departure_datetime = forms.DateTimeField(
        required=True,
        widget=forms.DateTimeInput(
            attrs={
                "type": "datetime-local",
                "class": "form-control",
                "min": timezone.now().strftime("%Y-%m-%dT%H:%M"),
            },
        ),
    )

    seats = forms.IntegerField(
        required=True,
        min_value=1,
        max_value=8,
        widget=forms.NumberInput(
            attrs={
                "placeholder": _("Number of seats available"),
                "class": "form-control",
            },
        ),
        help_text=_("Number of seats available in the carpool."),
    )

    price_per_seat = forms.DecimalField(
        required=True,
        min_value=0,
        decimal_places=2,
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

    def __init__(self, *args, **kwargs):
        self.ride = kwargs.pop("instance", None)
        super().__init__(*args, **kwargs)
        ride = self.ride

        if ride:
            self.fields["d_fulltext"].initial = ride.start_loc.fulltext
            self.fields["d_street"].initial = ride.start_loc.street
            self.fields["d_zipcode"].initial = ride.start_loc.zipcode
            self.fields["d_city"].initial = ride.start_loc.city
            self.fields["d_latitude"].initial = ride.start_loc.lat
            self.fields["d_longitude"].initial = ride.start_loc.lng

            self.fields["a_fulltext"].initial = ride.end_loc.fulltext
            self.fields["a_street"].initial = ride.end_loc.street
            self.fields["a_zipcode"].initial = ride.end_loc.zipcode
            self.fields["a_city"].initial = ride.end_loc.city
            self.fields["a_latitude"].initial = ride.end_loc.lat
            self.fields["a_longitude"].initial = ride.end_loc.lng

            # Guard access: duration or geometry may be None for legacy rides/tests
            if getattr(ride, "duration", None):
                try:
                    self.fields["r_duration"].initial = ride.duration.total_seconds() / 3600
                except Exception:
                    self.fields["r_duration"].initial = None
            else:
                self.fields["r_duration"].initial = None

            # Guard access: geometry may be None for legacy rides/tests or
            # accessing .geojson may raise on some geometry objects
            try:
                geom = getattr(ride, "geometry", None)
                if geom is not None:
                    # Use getattr for safety in case the object lacks geojson
                    self.fields["r_geometry"].initial = getattr(geom, "geojson", "") or ""
                else:
                    self.fields["r_geometry"].initial = ""
            except Exception:
                self.fields["r_geometry"].initial = ""

            self.fields["departure_datetime"].initial = timezone.localtime(
                ride.start_dt
            ).strftime("%Y-%m-%dT%H:%M")
            self.fields["seats"].initial = ride.vehicle.seats
            self.fields["seats"].min_value = (
                ride.booked_seats if ride.booked_seats > 0 else 1
            )
            self.fields["price_per_seat"].initial = ride.price
            self.fields["payment_method"].initial = [
                method for method in ride.payment_method
            ]
            self.fields["comment"].initial = ride.comment

    def clean(self):
        cleaned_data = super().clean()


        d_lat = cleaned_data.get("d_latitude")
        d_lng = cleaned_data.get("d_longitude")
        a_lat = cleaned_data.get("a_latitude")
        a_lng = cleaned_data.get("a_longitude")

        # Use a small tolerance for float comparisons
        if (d_lat is not None and a_lat is not None
            and d_lng is not None and a_lng is not None
            and abs(d_lat - a_lat) < 1e-5
            and abs(d_lng - a_lng) < 1e-5):
            self.add_error(
                "a_fulltext",
                _("Departure and arrival locations cannot be the same."),
            )

        price = cleaned_data.get("price_per_seat")
        payment = cleaned_data.get("payment_method")

        if price is not None and price > 0:
            if not payment:
                self.add_error(
                    "payment_method",
                    _("A payment method is required if a price is set."),
                )

        if price is not None and price > 999:
            self.add_error(
                "price_per_seat",
                _("The price per seat seems unreasonably high."),
            )

        # Ensure that the user cannot reduce the number of seats below the
        # number of already booked seats
        if self.ride:
            seats_input = cleaned_data.get("seats")
            if seats_input is not None and seats_input < self.ride.booked_seats:
                self.add_error(
                    "seats",
                    _(
                        "You cannot reduce the number of seats below the number of already booked seats (%(seats)s)."
                    )
                    % {"seats": self.ride.booked_seats},
                )

    def save(self, ride):
        ride.start_loc.fulltext = self.cleaned_data["d_fulltext"]
        ride.start_loc.street = self.cleaned_data["d_street"]
        ride.start_loc.zipcode = self.cleaned_data["d_zipcode"]
        ride.start_loc.city = self.cleaned_data["d_city"]
        ride.start_loc.lat = self.cleaned_data["d_latitude"]
        ride.start_loc.lng = self.cleaned_data["d_longitude"]
        ride.start_loc.save()

        ride.end_loc.fulltext = self.cleaned_data["a_fulltext"]
        ride.end_loc.street = self.cleaned_data["a_street"]
        ride.end_loc.zipcode = self.cleaned_data["a_zipcode"]
        ride.end_loc.city = self.cleaned_data["a_city"]
        ride.end_loc.lat = self.cleaned_data["a_latitude"]
        ride.end_loc.lng = self.cleaned_data["a_longitude"]
        ride.end_loc.save()

        ride.duration = datetime.timedelta(hours=self.cleaned_data["r_duration"])

        # Geometry should not change on edit
        ride.geometry = GEOSGeometry(self.cleaned_data["r_geometry"], srid=4326)

        ride.start_dt = self.cleaned_data["departure_datetime"]
        ride.vehicle.seats = self.cleaned_data["seats"]
        ride.price = self.cleaned_data["price_per_seat"]
        ride.payment_method = self.cleaned_data["payment_method"]
        ride.comment = self.cleaned_data["comment"]

        ride.vehicle.save()
        ride.save()
        return ride
