from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from carpool.models import Ride, JoinRequest
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods


@login_required
def index(request):
    outgoing_requests = JoinRequest.objects.filter(user=request.user)
    incoming_requests = JoinRequest.objects.filter(
        ride__in=request.user.rides_as_driver.all()
    )

    context = {
        "outgoing_requests": outgoing_requests,
        "incoming_requests": incoming_requests,
    }

    return render(request, "chat/index.html", context)


# TODO: move this elsewhere
@login_required
@require_http_methods(["POST"])
def change_jrequest_status(request, jr_pk):
    join_request = get_object_or_404(JoinRequest, pk=jr_pk)

    if request.user != join_request.ride.driver:
        return HttpResponse("You are not the driver of this post", status=403)

    action = request.POST.get("action")
    if action == "accept":
        join_request.status = JoinRequest.JoinRequestStatus.ACCEPTED
        # Add the user to the ride
        join_request.ride.rider.add(join_request.user)

    elif action == "decline":
        join_request.status = JoinRequest.JoinRequestStatus.DECLINED
        # Remove the user to the ride if they were added
        if join_request.user in join_request.ride.rider.all():
            join_request.ride.rider.remove(join_request.user)

    else:
        return HttpResponse("Invalid action", status=400)

    join_request.save()
    return redirect("chat:index")


@login_required
def room(request, jr_pk):
    join_request = get_object_or_404(JoinRequest, pk=jr_pk)

    # FIXME this seems wrong
    if request.user != join_request.ride.driver:
        with_user = join_request.ride.driver
    elif request.user == join_request.ride.driver:
        with_user = join_request.user
    else:
        # TODO: log if user is not allowed to access this room
        return HttpResponse("You are not allowed to access this room", status=403)

    shared_ride_count = Ride.objects.count_shared_ride(request.user, with_user)

    outgoing_requests = JoinRequest.objects.filter(user=request.user)
    incoming_requests = JoinRequest.objects.filter(
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
