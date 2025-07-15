from django.contrib import admin
from carpool.models import Ride, Vehicle, Location, Step, JoinRequest, ChatMessages


admin.site.register(Vehicle)
admin.site.register(Location)
admin.site.register(Step)
admin.site.register(JoinRequest)
admin.site.register(ChatMessages)


@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = ("uuid", "driver", "start_dt", "end_dt")
