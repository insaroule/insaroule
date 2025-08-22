from django.urls import path

from carpool.views import (
    api_auto_completion,
    api_routing,
    change_jrequest_status,
    list_my_rides,
    ride_map,
    rides_create,
    rides_edit,
    rides_detail,
    rides_list,
    rides_subscribe,
)

app_name = "carpool"

urlpatterns = [
    path("", rides_list, name="list"),
    path("my-rides/", list_my_rides, name="my-rides"),
    path("create/", rides_create, name="create"),
    path("<uuid:pk>/", rides_detail, name="detail"),
    path("<uuid:pk>/edit/", rides_edit, name="edit"),
    path("map/", ride_map, name="map"),
    path("<uuid:pk>/subscribe/", rides_subscribe, name="subscribe"),
    path("jr/<uuid:jr_pk>/status/", change_jrequest_status, name="change_jr_status"),
    # API endpoints
    path("api/completion/", api_auto_completion, name="completion"),
    path("api/routing/", api_routing, name="routing"),
]
