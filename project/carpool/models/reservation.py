from django.db import models
from django.utils.translation import gettext_lazy as _
from carpool.models.ride import Ride


class Reservation(models.Model):
    """
    The Reservation model represents a user's request to join a ride.
    It includes the status of the request, timestamps, and references to the user and ride.
    """

    class Status(models.TextChoices):
        PENDING = (
            "PENDING",
            _("Pending"),
        )  # The reservation is pending and awaiting driver action
        ACCEPTED = "ACCEPTED", _("Accepted")  # The driver accepted the reservation
        DECLINED = "DECLINED", _("Declined")  # The driver declined the reservation
        CANCELED = (
            "CANCELED",
            _("Canceled"),
        )  # The user that made the reservation canceled it

    status = models.CharField(
        verbose_name=_("status"),
        choices=Status.choices,
        max_length=10,
        help_text=_("Status of the join request"),
        default=Status.PENDING,
    )

    created_at = models.DateTimeField(
        verbose_name=_("created at"),
        help_text=_("The date and time when the reservation was created"),
        auto_now_add=True,
    )

    user = models.ForeignKey(
        "accounts.User",
        verbose_name=_("user"),
        help_text=_("The user who made the chat request"),
        related_name="reservations",
        on_delete=models.CASCADE,
    )

    ride = models.ForeignKey(
        Ride,
        verbose_name=_("ride"),
        help_text=_("The ride for which the chat request is made"),
        on_delete=models.CASCADE,
        related_name="reservations",
    )
