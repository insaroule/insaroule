import logging

from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import GEOSGeometry
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.timezone import timedelta, datetime

from carpool.forms import CreateRideStep1Form, CreateRideStep2Form, StopOverFormSet
from carpool.models import Location
from carpool.models.ride import Ride


@login_required
def create_step1(request):
    form = CreateRideStep1Form()
    formset = StopOverFormSet()

    if request.method == "POST":
        print(request.POST)
        form = CreateRideStep1Form(request.POST)
        formset = StopOverFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            # Store form data in session
            cleaned = form.cleaned_data.copy()

            # Convert datetime to string
            if "departure_datetime" in cleaned:
                cleaned["departure_datetime"] = cleaned[
                    "departure_datetime"
                ].isoformat()

            # TODO: store formset data in session as well

            request.session["ride_step1"] = cleaned
            request.session.modified = True
            return redirect("carpool:create_step2")

    context = {
        "form": form,
        "formset": formset,
    }
    return render(request, "rides/creation/step1.html", context)


@login_required
def create_step2(request):
    step1_data = request.session.get("ride_step1", None)
    if not step1_data:
        logging.info("Step 1 data not found in session, redirecting to step 1")
        return redirect("carpool:create_step1")

    form = CreateRideStep2Form()
    if request.method == "POST":
        form = CreateRideStep2Form(request.POST)
        if form.is_valid():
            # Create Location objects from step1_data if needed
            departure = Location.objects.get_or_create(
                fulltext=step1_data.pop("d_fulltext"),
                street=step1_data.pop("d_street"),
                zipcode=step1_data.pop("d_zipcode"),
                city=step1_data.pop("d_city"),
                lat=step1_data.pop("d_latitude"),
                lng=step1_data.pop("d_longitude"),
            )[0]

            arrival = Location.objects.get_or_create(
                fulltext=step1_data.pop("a_fulltext"),
                street=step1_data.pop("a_street"),
                zipcode=step1_data.pop("a_zipcode"),
                city=step1_data.pop("a_city"),
                lat=step1_data.pop("a_latitude"),
                lng=step1_data.pop("a_longitude"),
            )[0]

            # Compute datetime and geometry fields
            start_dt = datetime.fromisoformat(step1_data.pop("departure_datetime"))
            duration = timedelta(hours=step1_data.pop("r_duration", 0))

            step1_data["driver"] = request.user
            step1_data["geometry"] = GEOSGeometry(
                step1_data.pop("r_geometry", None), srid=4326
            )
            step1_data["start_dt"] = start_dt
            step1_data["end_dt"] = start_dt + duration
            step1_data["duration"] = duration
            step1_data["start_loc"] = departure
            step1_data["end_loc"] = arrival

            ride_data = {**step1_data, **form.cleaned_data}
            ride = Ride.objects.create(**ride_data)

            return redirect("carpool:detail", pk=ride.pk)

    context = {
        "step1_data": request.session.get("ride_step1", {}),
        "form": form,
        "departure_datetime": timezone.datetime.fromisoformat(
            step1_data["departure_datetime"]
        ),
        "payment_methods": Ride.PaymentMethod.choices,
    }
    return render(request, "rides/creation/step2.html", context)
