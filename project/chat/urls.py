from django.urls import path
from chat.views import (
    index,
    room,
    report,
    mod_center,
    mod_room,
    hide_message,
    unhide_message,
    user_report,
)

app_name = "chat"

urlpatterns = [
    path("", index, name="index"),
    path("<uuid:jr_pk>/", room, name="room"),
    path("<uuid:jr_pk>/report/", report, name="report"),
]

urlpatterns += [
    path("mod/", mod_center, name="mod_index"),
    path("mod/<uuid:jr_pk>/", mod_room, name="mod_room"),
    path("mod/msg/<int:id>/hide/", hide_message, name="hide_message"),
    path("mod/msg/<int:id>/unhide/", unhide_message, name="unhide_message"),
    path("mod/user/<uuid:user_pk>/report/", user_report, name="user_report"),
]
