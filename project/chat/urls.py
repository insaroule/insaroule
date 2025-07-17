from django.urls import path
from chat.views import index, room


app_name = "chat"

urlpatterns = [
    path("", index, name="index"),
    path("<uuid:jr_pk>/", room, name="room"),
]
