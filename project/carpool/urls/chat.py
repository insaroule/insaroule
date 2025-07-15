from django.urls import path
from carpool.views.chat import index, room


app_name = "chat"

urlpatterns = [
    path("", index, name="index"),
    path("<uuid:jr_pk>/", room, name="room"),
]
