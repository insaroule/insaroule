from django.shortcuts import render
from carpool.models import Ride
from django.contrib.auth.decorators import login_required


@login_required
def rides_list(request):
    context = {
        "rides": Ride.objects.all(),
    }
    return render(request, "rides/list.html", context)
