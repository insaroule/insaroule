from django.shortcuts import render

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from carpool.models import Ride
from chat.models import ChatRequest
from django.http import HttpResponse


@login_required
def index(request):
    outgoing_requests = ChatRequest.objects.filter(user=request.user)
    incoming_requests = ChatRequest.objects.filter(
        ride__in=request.user.rides_as_driver.all()
    )

    context = {
        "outgoing_requests": outgoing_requests,
        "incoming_requests": incoming_requests,
    }

    return render(request, "chat/index.html", context)


@login_required
def room(request, jr_pk):
    join_request = get_object_or_404(ChatRequest, pk=jr_pk)

    # FIXME this seems wrong
    if request.user != join_request.ride.driver:
        with_user = join_request.ride.driver
    elif request.user == join_request.ride.driver:
        with_user = join_request.user
    else:
        # TODO: log if user is not allowed to access this room
        return HttpResponse("You are not allowed to access this room", status=403)

    shared_ride_count = Ride.objects.count_shared_ride(request.user, with_user)

    outgoing_requests = ChatRequest.objects.filter(user=request.user)
    incoming_requests = ChatRequest.objects.filter(
        ride__in=request.user.rides_as_driver.all()
    )

    # Keep rides that are from today or in the future
    # others_rides_requests = others_rides_requests.filter(ride__start_dt__gte=timezone.now()).order_by("ride__start_dt")

    context = {
        "with_user": with_user,
        "join_request": join_request,
        "shared_ride_count": shared_ride_count,
        "outgoing_requests": outgoing_requests,
        "incoming_requests": incoming_requests,
    }
    return render(request, "chat/room.html", context)
