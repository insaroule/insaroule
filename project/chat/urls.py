from django.urls import path
from chat.views import (
    index,
    room,
    report,
    mod_center,
    mod_room,
    hide_message,
    unhide_message,
)

app_name = "chat"

urlpatterns = [
    path("", index, name="index"),
    path("<uuid:jr_pk>/", room, name="room"),
    path("<uuid:jr_pk>/report/", report, name="report"),
]

urlpatterns += [
    path("mod/", mod_center, name="moderation_center"),
    path("mod/<uuid:jr_pk>/", mod_room, name="moderation_room"),
    path("mod/msg/<int:id>/hide/", hide_message, name="hide_message"),
    path("mod/msg/<int:id>/unhide/", unhide_message, name="unhide_message"),
]
