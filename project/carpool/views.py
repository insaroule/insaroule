import datetime
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.gis.geos import GEOSGeometry, Point
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from carpool.models import Location
from carpool.models.ride import Ride
from django.contrib.auth.decorators import login_required
from carpool.forms import CreateRideForm
from carpool.tasks import get_autocompletion, get_routing
from asgiref.sync import sync_to_async
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from chat.models import ChatRequest
import json

from django.core.paginator import Paginator


@login_required
def ride_map(request):
    rides = Ride.objects.all()
    rides_geo = []

    for ride in rides:
        if ride.geometry:
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
                    "start_d": ride.start_dt.strftime("%A %d %B %Y"),
                    "start_t": ride.start_dt.strftime("%H:%M"),
                    "start_dt": ride.start_dt.isoformat(),
                    "price": ride.price,
                    "duration": f"{int(ride.duration.total_seconds() // 3600)}h {int((ride.duration.total_seconds() % 3600) // 60)}",
                }
            )

    context = {"rides_geo": rides_geo}
    return render(request, "rides/map.html", context)


@require_http_methods(["POST"])
def change_jrequest_status(request, jr_pk):
    join_request = get_object_or_404(ChatRequest, pk=jr_pk)

    if request.user != join_request.ride.driver:
        return HttpResponse("You are not the driver of this post", status=403)

    action = request.POST.get("action")
    if action == "accept":
        join_request.status = ChatRequest.Status.ACCEPTED
        # Add the user to the ride
        join_request.ride.rider.add(join_request.user)

    elif action == "decline":
        join_request.status = ChatRequest.Status.DECLINED
        # Remove the user to the ride if they were added
        if join_request.user in join_request.ride.rider.all():
            join_request.ride.rider.remove(join_request.user)

    else:
        return HttpResponse("Invalid action", status=400)

    join_request.save()
    return redirect("chat:index")


@login_required
def rides_subscribe(request, pk):
    ride = get_object_or_404(Ride, pk=pk)
    if request.method == "POST":
        ride.join_requests.create(user=request.user)
        return redirect("chat:index")
    return redirect("carpool:detail", pk=ride.pk)


@login_required
def rides_detail(request, pk):
    ride = get_object_or_404(Ride, pk=pk)
    context = {
        "ride": ride,
        "geometry": ride.geometry.geojson,
    }
    return render(request, "rides/detail.html", context)


@login_required
def rides_list(request):
    rides = Ride.objects.all()

    # ====================================================== #
    # Filters
    # ====================================================== #
    filter_date = request.GET.get("start_dt", "")
    filter_start = request.GET.get("d_latlng", "")
    filter_end = request.GET.get("a_latlng", "")

    if filter_date:
        # Get rides for a specific date
        filter_date = datetime.datetime.strptime(filter_date, "%Y-%m-%d").date()
        rides = rides.filter(start_dt__date=filter_date)
        print("Rides:", rides)

    if filter_start:
        # Do the postgis check if the location is within 10km of the geometry
        # Check if filter_start is in the format "longitude,latitude"
        try:
            lat, lng = map(float, filter_start.split(","))
            point = Point(lng, lat, srid=4326)  # (lng, lat) — correct order for GEOS
            print("Point:", point)
            # Annotate rides with distance from the point
            rides = rides.annotate(distance=Distance("geometry", point))
            rides = rides.filter(distance__lte=D(km=10))
        except ValueError:
            print("Invalid coordinates :", filter_start)
            return HttpResponse(
                "Invalid coordinates format for start location", status=400
            )

    if filter_end:
        # Do the postgis check if the location is within 10km of the geometry
        # Do nothing for now (or it will be to exclusive to the rides)
        pass

    rides = rides.annotate(ride_date=TruncDate("start_dt")).order_by(
        "ride_date", "start_dt"
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


@login_required
def rides_create(request):
    form = CreateRideForm()
    if request.method == "POST":
        form = CreateRideForm(request.POST)
        if form.is_valid():
            departure = Location.objects.get_or_create(
                fulltext=form.cleaned_data["d_fulltext"],
                street=form.cleaned_data["d_street"],
                zipcode=form.cleaned_data["d_zipcode"],
                city=form.cleaned_data["d_city"],
                lat=form.cleaned_data["d_latitude"],
                lng=form.cleaned_data["d_longitude"],
            )[0]

            arrival = Location.objects.get_or_create(
                fulltext=form.cleaned_data["a_fulltext"],
                street=form.cleaned_data["a_street"],
                zipcode=form.cleaned_data["a_zipcode"],
                city=form.cleaned_data["a_city"],
                lat=form.cleaned_data["a_latitude"],
                lng=form.cleaned_data["a_longitude"],
            )[0]

            print("Start_dt", form.cleaned_data["departure_datetime"])
            print(
                "End_dt",
                form.cleaned_data["departure_datetime"]
                + datetime.timedelta(hours=form.cleaned_data["r_duration"]),
            )
            print("Duration", datetime.timedelta(hours=form.cleaned_data["r_duration"]))

            ride = Ride.objects.create(
                driver=request.user,
                start_dt=form.cleaned_data["departure_datetime"],
                end_dt=form.cleaned_data["departure_datetime"]
                + datetime.timedelta(hours=form.cleaned_data["r_duration"]),
                start_loc=departure,
                end_loc=arrival,
                payment_method=form.cleaned_data["payment_method"],
                price=form.cleaned_data["price_per_seat"],
                geometry=GEOSGeometry(form.cleaned_data["r_geometry"], srid=4326),
                duration=datetime.timedelta(hours=form.cleaned_data["r_duration"]),
            )

            return redirect("carpool:detail", pk=ride.pk)

    context = {
        "form": form,
        "payment_methods": Ride.PaymentMethod.choices,
    }
    return render(request, "rides/create.html", context)


@login_required
async def api_auto_completion(request) -> JsonResponse:
    """
    An async API proxy endpoint to get latitude and
    longitude for a given query.
    """
    text = request.GET.get("text", "")
    if not text:
        return JsonResponse({"status": "NOK"}, status=400)

    task = get_autocompletion.delay(text)
    result = await sync_to_async(task.get)(timeout=5)  # blocking I/O offloaded
    return JsonResponse({"status": "OK", "results": result}, safe=False, status=200)


@login_required
async def api_routing(request) -> JsonResponse:
    """
    An async API proxy endpoint to get routing information.
    """
    start = request.GET.get("start", "")
    end = request.GET.get("end", "")
    if not start or not end:
        return JsonResponse({"status": "NOK"}, status=400)
    task = get_routing.delay(start, end)
    res = await sync_to_async(task.get)(timeout=5)  # blocking I/O offloaded
    return JsonResponse(res, safe=False)
