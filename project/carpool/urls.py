from django.urls import path

from carpool.views import (
    api_auto_completion,
    api_routing,
    change_jrequest_status,
    list_my_rides,
    ride_map,
    rides_create,
    rides_delete,
    rides_detail,
    rides_edit,
    rides_list,
    rides_subscribe,
    vehicles_create,
    vehicles_update,
)
from carpool.views import backoffice as bo_views

app_name = "carpool"

urlpatterns = [
    path("", rides_list, name="list"),
    path("my-rides/", list_my_rides, name="my-rides"),
    path("create/", rides_create, name="create"),
    path("<uuid:pk>/", rides_detail, name="detail"),
    path("<uuid:pk>/edit/", rides_edit, name="edit"),
    path("<uuid:pk>/delete/", rides_delete, name="delete"),
    path("map/", ride_map, name="map"),
    path("<uuid:pk>/subscribe/", rides_subscribe, name="subscribe"),
    path("jr/<uuid:jr_pk>/status/", change_jrequest_status, name="change_jr_status"),
    # API endpoints
    path("api/completion/", api_auto_completion, name="completion"),
    path("api/routing/", api_routing, name="routing"),
    path("api/vehicles/new/", vehicles_create, name="create_vehicle"),
    path("api/vehicles/<int:pk>/update/", vehicles_update, name="update_vehicle"),
]

# Back office specific URLs
urlpatterns += [
    path("back-office/statistics/", bo_views.statistics, name="bo_statistics"),
    path(
        "back-office/statistics/json/",
        bo_views.statistics_json_monthly,
        name="bo_statistics_json_monthly",
    ),
]
