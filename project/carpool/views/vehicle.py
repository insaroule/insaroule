from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
import logging
from carpool.forms.vehicle import VehicleForm
from carpool.models import Vehicle


@login_required
def create(request):
    form = VehicleForm()
    if request.method == "POST":
        form = VehicleForm(request.POST)
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.driver = request.user
            vehicle.save()
            logging.info(f"Vehicle {vehicle.pk} created by user {request.user.pk}")
            return JsonResponse(
                {
                    "status": "OK",
                    "vehicle": {
                        "id": vehicle.pk,
                        "name": vehicle.name,
                        "description": vehicle.description,
                        "seats": vehicle.seats,
                        "geqCO2_per_km": vehicle.geqCO2_per_km,
                    },
                },
                status=201,
            )
        else:
            logging.error(f"Vehicle creation form invalid: {form.errors}")
            return JsonResponse({"status": "NOK", "errors": form.errors}, status=400)
    return JsonResponse(
        {"status": "NOK", "error": "Invalid request method"}, status=400
    )


@login_required
@require_http_methods(["POST"])
def update(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    if vehicle.driver != request.user:
        return JsonResponse(
            {"status": "NOK", "error": "You are not the driver of this vehicle"},
            status=403,
        )

    form = VehicleForm(request.POST, instance=vehicle)
    if form.is_valid():
        form.save()
        logging.info(f"Vehicle {vehicle.pk} updated by user {request.user.pk}")
        return JsonResponse(
            {
                "status": "OK",
                "vehicle": {
                    "id": vehicle.pk,
                    "name": vehicle.name,
                    "description": vehicle.description,
                    "seats": vehicle.seats,
                    "geqCO2_per_km": vehicle.geqCO2_per_km,
                },
            },
            status=201,
        )
    return JsonResponse({"status": "NOK", "errors": form.errors}, status=400)
