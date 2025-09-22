from django.urls import path

from carpool.views import (
    update_reservation,
    cancel_reservation,
    list_my_rides,
    ride_map,
    rides_create,
    rides_delete,
    rides_detail,
    rides_edit,
    rides_list,
    rides_subscribe,
)
from carpool.views import api as api_views
from carpool.views import backoffice as bo_views
from carpool.views import vehicle as vehicle_views
from chat.views import request_chat

app_name = "carpool"

urlpatterns = [
    path("", rides_list, name="list"),
    path("my-rides/", list_my_rides, name="my-rides"),
    path("create/", rides_create, name="create"),
    path("<uuid:pk>/", rides_detail, name="detail"),
    path("<uuid:pk>/edit/", rides_edit, name="edit"),
    path("<uuid:pk>/delete/", rides_delete, name="delete"),
    path("map/", ride_map, name="map"),
    path("<uuid:ride_pk>/chat/", request_chat, name="chat"),
    path("<uuid:ride_pk>/subscribe/", rides_subscribe, name="subscribe"),
]

# API endpoints
urlpatterns += [
    path("api/reservations/cancel/", cancel_reservation, name="cancel_reservation"),
    path("api/reservations/update/", update_reservation, name="update_reservation"),
    path("api/vehicles/new/", vehicle_views.create, name="create_vehicle"),
    path("api/vehicles/<int:pk>/update/", vehicle_views.update, name="update_vehicle"),
    path("api/completion/", api_views.autocompletion, name="completion"),
    path("api/routing/", api_views.routing, name="routing"),
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
