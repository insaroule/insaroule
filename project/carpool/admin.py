from django.contrib import admin

from carpool.models import Location, Step, Vehicle
from carpool.models.ride import Ride
from carpool.models.statistics import Statistics, MonthlyStatistics

admin.site.register(Location)
admin.site.register(Step)

admin.site.register(Statistics)


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("name", "driver", "seats", "description", "geqCO2_per_km")


@admin.register(MonthlyStatistics)
class MonthlyStatisticsAdmin(admin.ModelAdmin):
    list_display = ("month", "year", "total_rides", "total_distance", "total_co2")


@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = ("uuid", "driver", "start_dt", "end_dt")
