from uuid import uuid4

from carpool.models.ride import Ride
from django.urls import reverse
from django.db import models
from django.utils.translation import gettext_lazy as _


# Create your models here.
class ChatRequest(models.Model):
    # class Status(models.TextChoices):
    #     PENDING = "PENDING", _("Pending")
    #     ACCEPTED = "ACCEPTED", _("Accepted")
    #     DECLINED = "DECLINED", _("Declined")

    uuid = models.UUIDField(
        verbose_name=_("UUID"),
        primary_key=True,
        editable=False,
        default=uuid4,
    )

    # status = models.CharField(
    #     verbose_name=_("status"),
    #     choices=Status.choices,
    #     max_length=10,
    #     help_text=_("Status of the join request"),
    #     default=Status.PENDING,
    # )

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

    def get_room_url(self):
        return reverse("chat:room", kwargs={"jr_pk": self.pk})

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

    chat_request = models.ForeignKey(
        ChatRequest,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name=_("join request"),
    )

    timestamp = models.DateTimeField(auto_now_add=True)

    hidden = models.BooleanField(
        default=False,
        verbose_name=_("hidden"),
        help_text=_("Indicates whether this message is hidden from regular users"),
    )

    read_at = models.DateTimeField(
        auto_now_add=False,
        blank=True,
        null=True,
        verbose_name=_("read at"),
        help_text=_("The date and time when the message was read"),
    )

    notified_at = models.DateTimeField(
        auto_now_add=False,
        blank=True,
        null=True,
        verbose_name=_("notified at"),
        help_text=_(
            "The date and time when the user was notified about this message (if any)"
        ),
    )

    class Meta:
        # Custom permission to moderate chat messages
        permissions = (("can_moderate_messages", _("Can moderate chat messages")),)


class ChatReport(models.Model):
    chat_request = models.ForeignKey(
        ChatRequest,
        on_delete=models.CASCADE,
        related_name="reports",
        verbose_name=_("chat request"),
    )

    reported_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="chat_reports",
        verbose_name=_("reported by"),
    )

    reason = models.TextField(verbose_name=_("reason"), blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ChatReport({self.chat_request.uuid} by {self.reported_by.username})"


class ModAction(models.Model):
    class Action(models.TextChoices):
        FLAG_USER = "FLAG_USER", _("Flag User")  # Add a flag action
        BLOCK_USER = "BLOCK_USER", _("Block User")  # Block a user

    performed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="mod_actions",
        verbose_name=_("performed by"),
    )

    on_user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="mod_actions_on_user",
        verbose_name=_("on user"),
        blank=True,
        null=True,
    )

    reason = models.TextField(
        verbose_name=_("reason"),
        help_text=_("Reason for the moderation action"),
        blank=True,
        null=True,
    )

    action = models.CharField(
        max_length=20,
        choices=Action.choices,
        verbose_name=_("action"),
        help_text=_("The type of moderation action performed"),
    )

    timestamp = models.DateTimeField(auto_now_add=True)
