from django.shortcuts import render
from carpool.models import Ride


def rides_list(request):
    context = {
        "rides": Ride.objects.all(),
    }
    return render(request, "rides/list.html", context)
