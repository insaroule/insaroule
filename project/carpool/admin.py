from django.contrib import admin
from carpool.models import Ride, Vehicle, Location, Step

admin.site.register(Vehicle)
admin.site.register(Location)
admin.site.register(Step)


@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = ("id", "driver", "start_dt", "end_dt")
