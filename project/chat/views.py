import logging

from accounts.models import User
from carpool.models.reservation import Reservation
from carpool.models.ride import Ride
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import OuterRef, Q, Subquery
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods
from django.contrib.sites.shortcuts import get_current_site
from django.utils import timezone

from chat.models import ChatMessage, ChatReport, ChatRequest, ModAction
from chat.tasks import send_email_report_to_mods


@login_required
def request_chat(request, ride_pk):
    """Create a chat request for a given ride."""
    ride = get_object_or_404(Ride, pk=ride_pk)
    if request.method == "POST":
        if ChatRequest.objects.filter(user=request.user, ride=ride).exists():
            logging.warning(
                f"User {request.user} has made a chat request about ride {ride.pk}"
            )
            messages.error(
                request, _("You have already requested to chat about this ride.")
            )
            return redirect("carpool:detail", pk=ride.pk)

        chat_request = ride.join_requests.create(user=request.user)

        return redirect("chat:room", jr_pk=chat_request.pk)
    return redirect("carpool:detail", pk=ride.pk)


@login_required
def report(request, jr_pk):
    join_request = get_object_or_404(ChatRequest, pk=jr_pk)

    if request.method == "POST":
        # check if the user is a participant in the chat
        if request.user not in [join_request.user, join_request.ride.driver]:
            return HttpResponse(
                "You are not allowed to report this chat request", status=403
            )

        # Check if the user has already reported this chat request
        if ChatReport.objects.filter(
            chat_request=join_request, reported_by=request.user
        ).exists():
            messages.error(request, _("You have already reported this chat request."))
            return redirect("chat:room", jr_pk=jr_pk)

        # Handle the report submission
        ChatReport.objects.create(
            chat_request=join_request,
            reported_by=request.user,
            reason=request.POST.get("reason", ""),
        )

        # Notify moderators via email (asynchronous task)
        site_base_url = request.scheme + "://" + get_current_site(request).domain
        send_email_report_to_mods.delay(join_request.pk, site_base_url)

    messages.info(request, _("The chat request has been reported."))
    return redirect("chat:room", jr_pk=jr_pk)


@permission_required("chat.can_moderate_messages", raise_exception=True)
@require_http_methods(["POST"])
def user_report(request, user_pk):
    user = get_object_or_404(User, pk=user_pk)
    join_request = get_object_or_404(
        ChatRequest,
        pk=request.POST.get("join_request_id"),
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


@permission_required("chat.can_moderate_messages", raise_exception=True)
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
    query_ride = request.GET.get("ride", "")
    query_username = request.GET.get("search_by_username", "")
    query_content = request.GET.get("search_by_content", "")
    past_rides = request.GET.get("past", "")

    reports = ChatRequest.objects.all()

    if not past_rides == "1":
        reports = reports.filter(
            ride__start_dt__gte=timezone.now() - timezone.timedelta(days=1)
        )

    reports = reports.order_by("-created_at")

    if query_username:
        print(f"Searching by username: {query_username}")
        reports = reports.filter(
            Q(user__username__icontains=query_username)
            | Q(ride__driver__username__icontains=query_username)
        )
    if query_content:
        print(f"Searching by content: {query_content}")
        reports = reports.filter(Q(messages__content__icontains=query_content))

    if query_ride:
        print(f"Filtering by ride: {query_ride}")
        reports = reports.filter(ride__pk=query_ride)

    paginator = Paginator(reports, 10)  # Show 10 reports per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "search_by_username": query_username,
        "search_by_content": query_content,
        "ride": query_ride,
    }
    return render(request, "chat/moderation/index.html", context)


def get_sidebar_context(request):
    """
    Get the context for the sidebar, including outgoing and incoming chat requests.
    Used to avoid code duplication in multiple views.
    """

    # Subquery to fetch the last reservation status
    last_reservation = Reservation.objects.filter(
        ride=OuterRef("ride"),
        user=OuterRef("user"),
    ).order_by("-created_at")

    outgoing_requests = (
        ChatRequest.objects.filter(user=request.user)
        .annotate(
            last_reservation_status=Subquery(last_reservation.values("status")[:1])
        )
        .order_by("ride__start_dt")
    )

    # Print last_reservation_status for debugging

    incoming_requests = (
        ChatRequest.objects.filter(ride__in=request.user.rides_as_driver.all())
        .annotate(
            last_reservation_status=Subquery(last_reservation.values("status")[:1])
        )
        .order_by("ride__start_dt")
    )

    print("Outgoing Requests with last_reservation_status:")
    for jr in outgoing_requests:
        print(
            f"JoinRequest ID: {jr.pk}, Last Reservation Status: {jr.last_reservation_status}"
        )
    print("Incoming Requests with last_reservation_status:")
    for jr in incoming_requests:
        print(
            f"JoinRequest ID: {jr.pk}, Last Reservation Status: {jr.last_reservation_status}"
        )

    # Filtering for declined (if you re-enable later)
    # if not request.GET.get("o_declined"):
    #     outgoing_requests = outgoing_requests.exclude(
    #         last_reservation_status="DECLINED"
    #     )

    # if not request.GET.get("i_declined"):
    #     incoming_requests = incoming_requests.exclude(
    #         last_reservation_status="DECLINED"
    #     )

    # Pagination
    o_paginator = Paginator(outgoing_requests, 4)
    i_paginator = Paginator(incoming_requests, 4)

    o_page_number = request.GET.get("o_page")
    i_page_number = request.GET.get("i_page")

    outgoing_requests = o_paginator.get_page(o_page_number)
    incoming_requests = i_paginator.get_page(i_page_number)

    return {
        "outgoing_requests": outgoing_requests,
        "incoming_requests": incoming_requests,
    }


@login_required
def index(request):
    context = get_sidebar_context(request)
    return render(request, "chat/index.html", context)


@login_required
def room(request, jr_pk):
    join_request = get_object_or_404(ChatRequest, pk=jr_pk)

    if request.user not in [join_request.user, join_request.ride.driver]:
        return HttpResponse("You are not allowed to access this room", status=403)

    if request.user == join_request.user:
        with_user = join_request.ride.driver
    else:
        with_user = join_request.user

    shared_ride_count = Ride.objects.count_shared_ride(request.user, with_user)

    reservation = (
        join_request.ride.reservations.filter(user=join_request.user)
        .order_by("-created_at")
        .first()
    )

    context = {
        "with_user": with_user,
        "reservation": reservation,
        "join_request": join_request,
        "shared_ride_count": shared_ride_count,
        "has_booked_ride": reservation is not None,
    }
    # Inject sidebar context
    context.update(get_sidebar_context(request))

    return render(request, "chat/room.html", context)
