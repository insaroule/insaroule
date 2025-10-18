from django.contrib import admin

from carpool.models import Location, Step, Vehicle
from carpool.models.ride import Ride
from carpool.models.statistics import Statistics, MonthlyStatistics
from carpool.models.reservation import Reservation
from carpool.tasks import send_email_suggest_ride_sharing

from django.contrib import messages

admin.site.register(Location)
admin.site.register(Step)

admin.site.register(Statistics)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("pk", "user", "created_at", "status")
    list_filter = ("status", "created_at")
    search_fields = ("user__username", "user__email")


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("name", "driver", "seats", "description", "geqCO2_per_km")


@admin.register(MonthlyStatistics)
class MonthlyStatisticsAdmin(admin.ModelAdmin):
    list_display = ("month", "year", "total_rides", "total_distance", "total_co2")


@admin.action(description="Suggest drivers to share their ride")
def suggest_driver_to_share_ride(modeladmin, request, queryset):
    """
    This admin action send an email to the drivers of the selected rides suggesting them to share their ride.
    because they have similar start and end locations and times.
    """
    # Check if there are at least 2 rides
    if len(queryset) < 2:
        messages.error(request, "Please select at least 2 rides.")
        return

    # Check if all the rides are in the same day
    days = set(ride.start_dt.date() for ride in queryset)
    if len(days) > 1:
        messages.error(request, "Please select rides from the same day.")
        return

    # Check if there are at least 2 different drivers
    drivers = set(ride.driver for ride in queryset)
    if len(drivers) < 2:
        messages.error(
            request, "Please select rides from at least 2 different drivers."
        )
        return

    # Perform the action
    for ride in queryset:
        # Exclude the current ride from the queryset to find similar rides
        similar_rides = queryset.exclude(pk=ride.pk)

        send_email_suggest_ride_sharing.delay(
            ride.pk, [r.pk for r in similar_rides], request.user.pk
        )

    messages.info(request, "Suggestion emails have been sent to the drivers.")


class RideAdmin(admin.ModelAdmin):
    list_display = ("uuid", "driver", "start_dt", "end_dt")
    list_filter = ("start_dt", "driver")
    search_fields = (
        "driver__username",
        "driver__email",
        "start_loc__fulltext",
        "end_loc__fulltext",
    )
    actions = [suggest_driver_to_share_ride]


admin.site.register(Ride, RideAdmin)
