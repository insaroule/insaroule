import logging

from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import GEOSGeometry
from django.shortcuts import redirect, render, get_object_or_404
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.utils.timezone import timedelta, datetime
from django.contrib import messages
from django.utils.translation import gettext as _

from carpool.forms.ride import CreateRideStep1Form, CreateRideStep2Form, EditRideForm
from carpool.models import Step
from carpool.models.ride import Ride
from carpool.utils import get_or_create_location


@login_required
def create_step1(request):
    """First step of the ride creation process"""
    form = CreateRideStep1Form()

    if request.method == "POST":
        form = CreateRideStep1Form(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data.copy()

            cleaned["departure"] = form.departure.cleaned_data
            cleaned["stopovers"] = form.stopovers.cleaned_data.copy()
            cleaned["arrival"] = form.arrival.cleaned_data

            # Convert datetime to string
            if "departure_datetime" in cleaned:
                cleaned["departure_datetime"] = cleaned[
                    "departure_datetime"
                ].isoformat()

            request.session["ride_step1"] = cleaned
            request.session.modified = True
            return redirect("carpool:create_step2")
    # else:
    #     saved_data = request.session.get("ride_step1", None)
    #     if saved_data:
    #         form = CreateRideStep1Form(initial=saved_data)
    #     else:
    #         form = CreateRideStep1Form()

    context = {
        "form": form,
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
            # Create or get locations
            d_data = step1_data.pop("departure")
            departure = get_or_create_location(d_data)
            a_data = step1_data.pop("arrival")
            arrival = get_or_create_location(a_data)
            stopovers_data = step1_data.pop("stopovers", [])

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

            # Handle stopovers
            for index, stepover in enumerate(stopovers_data):
                so_location = get_or_create_location(stepover)
                step = Step.objects.create(
                    order=index + 1,
                    location=so_location,
                )
                ride.steps.add(step)

            return redirect("carpool:detail", pk=ride.pk)

    context = {
        "step1_data": request.session.get("ride_step1", {}),
        "stepover_data": step1_data.get("stopovers", []),
        "form": form,
        "departure_datetime": timezone.datetime.fromisoformat(
            step1_data["departure_datetime"]
        ),
        "payment_methods": Ride.PaymentMethod.choices,
    }
    return render(request, "rides/creation/step2.html", context)


@login_required
def edit(request, pk):
    ride = get_object_or_404(Ride, pk=pk)
    # Check if user has permission
    if ride.driver != request.user:
        raise PermissionDenied("You do not have permission to edit this ride.")

    form = EditRideForm(
        instance=ride,
    )

    if request.method == "POST":
        form = EditRideForm(request.POST, instance=ride)
        if form.is_valid():
            print(request.POST)
            form.save(ride)
            messages.success(request, _("You successfully updated the ride."))
            return redirect("carpool:detail", pk=ride.pk)

    context = {
        "ride": ride,
        "geometry": ride.geometry.geojson,
        "form": form,
        # "formset": fosrmset,
        "payment_methods": Ride.PaymentMethod.choices,
    }

    return render(request, "rides/edit.html", context)
