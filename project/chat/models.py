from uuid import uuid4
from django.utils.translation import gettext_lazy as _
from carpool.models.ride import Ride
from django.db import models


# Create your models here.
class ChatRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        ACCEPTED = "ACCEPTED", _("Accepted")
        DECLINED = "DECLINED", _("Declined")

    uuid = models.UUIDField(
        verbose_name=_("UUID"),
        primary_key=True,
        editable=False,
        default=uuid4,
    )

    status = models.CharField(
        verbose_name=_("status"),
        choices=Status.choices,
        max_length=10,
        help_text=_("Status of the join request"),
        default=Status.PENDING,
    )

    ride = models.ForeignKey(
        Ride,
        verbose_name=_("ride"),
        help_text=_("The ride for which the chat request is made"),
        on_delete=models.CASCADE,
        related_name="join_requests",
    )

    user = models.ForeignKey(
        "accounts.User",
        verbose_name=_("user"),
        help_text=_("The user who made the chat request"),
        related_name="join_requests",
        on_delete=models.CASCADE,
    )

    created_at = models.DateTimeField(
        verbose_name=_("created at"),
        help_text=_("The date and time when the chat request was created"),
        auto_now_add=True,
    )

    def __str__(self):
        return f"ChatRequest({self.user.username} for {self.ride.uuid})"


class ChatMessage(models.Model):
    content = models.TextField()
    sender = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="chat_messages",
        verbose_name=_("sender"),
    )

    join_request = models.ForeignKey(
        ChatRequest,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name=_("join request"),
    )

    timestamp = models.DateTimeField(auto_now_add=True)
