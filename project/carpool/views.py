import datetime
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
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

from django.core.paginator import Paginator


@login_required
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
    }
    return render(request, "rides/detail.html", context)


@login_required
def rides_list(request):
    ride_list = Ride.objects.annotate(ride_date=TruncDate("start_dt")).order_by(
        "ride_date", "start_dt"
    )

    paginator = Paginator(ride_list, 4)  # Show 4 rides per page.

    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    querydict = request.GET.copy()
    if "page" in querydict:
        querydict.pop("page")
    querystring = querydict.urlencode()

    context = {
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
                geometry=form.cleaned_data["r_geometry"],
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
