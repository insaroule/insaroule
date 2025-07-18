from django.shortcuts import redirect, render

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from carpool.models.ride import Ride
from accounts.models import User
from chat.models import ChatRequest, ChatReport, ModAction, ChatMessage
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator


@login_required
def report(request, jr_pk):
    join_request = get_object_or_404(ChatRequest, pk=jr_pk)

    if request.method == "POST":
        # Handle the report submission
        ChatReport.objects.create(
            chat_request=join_request,
            reported_by=request.user,
            reason=request.POST.get("reason", ""),
        )
    return redirect("chat:room", jr_pk=jr_pk)


@permission_required("chat.can_moderate_messages", raise_exception=True)
@require_http_methods(["POST"])
def user_report(request, user_pk):
    user = get_object_or_404(User, pk=user_pk)
    join_request = get_object_or_404(
        ChatRequest, pk=request.POST.get("join_request_id")
    )

    # Handle the user report submission
    ModAction.objects.create(
        performed_by=request.user,
        action=ModAction.Action.FLAG_USER,
        reason=request.POST.get("reason", ""),
        on_user=user,
    )

    return redirect("chat:mod_room", jr_pk=join_request.pk)


@permission_required("chat.can_moderate_messages", raise_exception=True)
def hide_message(request, id):
    message = get_object_or_404(ChatMessage, pk=id)
    message.hidden = True
    message.save()
    return JsonResponse({"status": "success"})


def unhide_message(request, id):
    message = get_object_or_404(ChatMessage, pk=id)
    message.hidden = False
    message.save()
    return JsonResponse({"status": "success"})


@permission_required("chat.can_moderate_messages", raise_exception=True)
def mod_room(request, jr_pk):
    join_request = get_object_or_404(ChatRequest, pk=jr_pk)
    context = {"join_request": join_request}
    return render(request, "chat/moderation/room.html", context)


@permission_required("chat.can_moderate_messages", raise_exception=True)
def mod_center(request):
    reports = ChatRequest.objects.all()
    paginator = Paginator(reports, 10)  # Show 10 reports per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
    }
    return render(request, "chat/moderation/index.html", context)


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
