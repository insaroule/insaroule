import datetime
import json

from chat.models import ChatRequest
from carpool.tasks import (
    send_email_confirmed_ride,
    send_email_declined_ride,
    send_email_incoming_reservation_to_driver,
)
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.core.paginator import Paginator
from django.db.models import Count, ExpressionWrapper, F, IntegerField
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.timezone import localtime
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods
from carpool.templatetags.duration import duration

from carpool.models.reservation import Reservation
from carpool.models.ride import Ride

import logging


@login_required
def list_my_rides(request):
    p_rides = Ride.objects.filter(driver=request.user).order_by("start_dt")
    s_rides = Reservation.objects.filter(user=request.user).order_by("ride__start_dt")

    s_paginator = Paginator(s_rides, 3)
    p_paginator = Paginator(p_rides, 3)

    s_page_num = request.GET.get("s_page")
    p_page_num = request.GET.get("p_page")

    s_page_obj = s_paginator.get_page(s_page_num)
    p_page_obj = p_paginator.get_page(p_page_num)

    context = {
        "s_page_obj": s_page_obj,
        "p_page_obj": p_page_obj,
    }

    return render(request, "rides/my_rides.html", context)


@login_required
def rides_map(request):
    rides = Ride.objects.filter_upcoming()
    rides_geo = []

    for ride in rides:
        if ride.geometry:
            start_dt_local = localtime(ride.start_dt)
            rides_geo.append(
                {
                    "start": [ride.start_loc.lat, ride.start_loc.lng],
                    "end": [ride.end_loc.lat, ride.end_loc.lng],
                    "geometry": json.loads(
                        ride.geometry.geojson
                    ),  # supposé être une chaîne GeoJSON valide
                    "uuid": str(ride.uuid),
                    "start_name": ride.start_loc.fulltext,
                    "start_lat": ride.start_loc.lat,
                    "start_lon": ride.start_loc.lng,
                    "end_name": ride.end_loc.fulltext,
                    "end_lat": ride.end_loc.lat,
                    "end_lon": ride.end_loc.lng,
                    "start_dt": start_dt_local.isoformat(),
                    "price": ride.price,
                    "duration": duration(ride.duration),
                }
            )

    context = {"rides_geo": rides_geo}
    return render(request, "rides/map.html", context)


@require_http_methods(["POST"])
@login_required
def cancel_reservation(request):
    reservation = get_object_or_404(Reservation, pk=request.POST.get("reservation_pk"))
    next_url = request.GET.get("next", reverse("chat:index"))

    if request.user != reservation.user:
        # Only the user who made the reservation can cancel it
        return HttpResponse(
            "You are not allowed to cancel this reservation", status=403
        )

    if reservation.status == Reservation.Status.CANCELED:
        messages.warning(request, _("This reservation is already canceled."))
        return HttpResponse("This reservation is already canceled", status=400)

    reservation.status = Reservation.Status.CANCELED

    if reservation.user in reservation.ride.rider.all():
        # Check if the user is already in the ride's riders
        messages.warning(request, _("You have been removed from the ride's riders."))
        reservation.ride.rider.remove(reservation.user)

    messages.warning(request, _("You have successfully canceled your reservation."))
    reservation.save()
    return redirect(next_url)


@require_http_methods(["POST"])
@login_required
def update_reservation(request):
    reservation = get_object_or_404(Reservation, pk=request.POST.get("reservation_pk"))
    next_url = request.GET.get("next", reverse("chat:index"))

    if request.user != reservation.ride.driver:
        return HttpResponse("You are not the driver of this ride.", status=403)

    if reservation.status == Reservation.Status.CANCELED:
        return HttpResponse("This reservation is already canceled.", status=400)

    action = request.POST.get("action")

    if action == "accept":
        reservation.status = Reservation.Status.ACCEPTED
        send_email_confirmed_ride.delay(reservation.pk)
        reservation.ride.rider.add(reservation.user)

    elif action == "decline":
        reservation.status = Reservation.Status.DECLINED
        if reservation.user in reservation.ride.rider.all():
            # Check if the user is already in the ride's riders
            reservation.ride.rider.remove(reservation.user)

        send_email_declined_ride.delay(reservation.pk)
    else:
        return HttpResponse("Invalid action", status=400)

    reservation.save()
    return redirect(next_url)


@login_required
def rides_subscribe(request, ride_pk):
    """Create a reservation for the given ride."""
    ride = get_object_or_404(Ride, pk=ride_pk)
    if request.method == "POST":
        # Get the chat request
        ChatRequest.objects.get(user=request.user, ride=ride)

        if Reservation.objects.filter(
            user=request.user, ride=ride, status__in=["DECLINED", "ACCEPTED"]
        ).exists():
            logging.warning(f"User {request.user} has already booked ride {ride.pk}")
            messages.error(request, _("You have already booked this ride."))
            return redirect("carpool:detail", pk=ride.pk)

        # Subscribe the user to the ride
        reservation = ride.reservations.create(user=request.user)
        logging.info(f"User {request.user} booked ride {ride.pk}")

        site_url = request.scheme + "://" + request.get_host()
        send_email_incoming_reservation_to_driver.delay(
            site_url,
            reservation_pk=reservation.pk,
        )

        messages.success(request, _("You have successfully booked this ride."))

        # Redirect to chat:room with join_request associated to this user and ride
        join_request = ChatRequest.objects.filter(user=request.user, ride=ride).first()
        if join_request:
            return redirect("chat:room", jr_pk=join_request.pk)
        return redirect("chat:index")

        messages.info(request, _("You subscribed to this ride."))

    return redirect("carpool:detail", pk=ride.pk)


@login_required
def rides_detail(request, pk):
    # Check if the user has already booked this ride
    # used to disabled the subscribe button
    reservation = request.user.reservations.filter(
        ride__pk=pk, status__in=["PENDING", "ACCEPTED", "DECLINED"]
    ).first()
    chat_request = ChatRequest.objects.filter(user=request.user, ride__pk=pk).first()

    ride = get_object_or_404(Ride, pk=pk)
    steps = ride.steps.order_by("order")

    steps_json = [
        {"lat": step.location.lat, "lng": step.location.lng} for step in steps
    ]

    context = {
        "ride": ride,
        "steps_json": steps_json,
        "geometry": ride.geometry.geojson,
        "reservation": reservation,
        "chat_request": chat_request,
    }

    return render(request, "rides/detail.html", context)


@login_required
def rides_delete(request, pk):
    ride = get_object_or_404(Ride, pk=pk)
    # Check if user has permission
    if ride.driver != request.user:
        return HttpResponse("You are not the driver of this ride", status=403)

    if request.method == "POST":
        if Ride.objects.safe_delete(ride):
            messages.success(request, _("You successfully deleted the ride."))
        else:
            messages.error(
                request,
                _(
                    "You cannot delete this ride because it has riders and is not over yet."
                ),
            )
            return redirect("carpool:detail", pk=ride.pk)
        return redirect("carpool:my-rides")

    context = {"ride": ride, "geometry": ride.geometry.geojson}
    return render(request, "rides/delete.html", context)


def rides_list(request):
    if not settings.ANONYMOUS_ACCESS_RIDES_LIST and not request.user.is_authenticated:
        # We have a global setting that disable anonymous access to the rides list
        return redirect(f"{reverse('accounts:login')}?next={request.path}")

    # Get all rides that are whether today's date or in the future
    rides = Ride.objects.filter_upcoming()

    # ====================================================== #
    # Filters
    # ====================================================== #
    filter_date = request.GET.get("start_dt", "")
    filter_start = request.GET.get("d_latlng", "")
    filter_end = request.GET.get("a_latlng", "")

    rides = rides.annotate(
        booked_seats_count=Count("rider", distinct=True),
        remaining_seats_count=ExpressionWrapper(
            F("vehicle__seats") - Count("rider", distinct=True),
            output_field=IntegerField(),
        ),
    ).exclude(remaining_seats_count__lte=0)

    if filter_date:
        # Get rides for a specific date
        filter_date = datetime.datetime.strptime(filter_date, "%Y-%m-%d").date()
        rides = rides.filter(start_dt__date=filter_date)

    if filter_start:
        # Do the postgis check if the location is within 10km of the geometry
        # Check if filter_start is in the format "longitude,latitude"
        try:
            lat, lng = map(float, filter_start.split(","))
            point = Point(lng, lat, srid=4326)  # (lng, lat) — correct order for GEOS
            # Annotate rides with distance from the point
            rides = rides.annotate(distance=Distance("geometry", point))
            rides = rides.filter(distance__lte=D(km=10))
        except ValueError:
            print("Invalid coordinates :", filter_start)
            return HttpResponse(
                "Invalid coordinates format for start location",
                status=400,
            )

    if filter_end:
        # Do the postgis check if the location is within 10km of the geometry
        # Do nothing for now (or it will be to exclusive to the rides)
        # TODO: implement it properly
        pass

    rides = rides.annotate(ride_date=TruncDate("start_dt")).order_by(
        "ride_date",
        "start_dt",
    )

    paginator = Paginator(rides, 4)  # Show 4 rides per page.

    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    querydict = request.GET.copy()
    if "page" in querydict:
        querydict.pop("page")
    querystring = querydict.urlencode()

    context = {
        "filter_date": filter_date,
        "d_fulltext": request.GET.get("d_fulltext", ""),
        "filter_departure": request.GET.get("d_latlng", ""),
        "filter_arrival": request.GET.get("a_latlng", ""),
        "a_fulltext": request.GET.get("a_fulltext", ""),
        "rides": page_obj.object_list,
        "page_obj": page_obj,
        "querystring": querystring,
    }
    return render(request, "rides/list.html", context)
