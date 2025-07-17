from django.contrib import admin
from carpool.models import Vehicle, Location, Step
from carpool.models.ride import Ride


admin.site.register(Vehicle)
admin.site.register(Location)
admin.site.register(Step)


@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = ("uuid", "driver", "start_dt", "end_dt")
