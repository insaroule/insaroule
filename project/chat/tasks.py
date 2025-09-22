from collections import defaultdict

from accounts.models import User
from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.core.mail import EmailMessage
from django.db.models import Case, Count, F, When
from django.db.models.fields import UUIDField
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from django.utils import timezone

from chat.models import ChatMessage

logger = get_task_logger(__name__)


@shared_task
def send_email_unread_messages():
    # We want to notify users about unread messages that are older than a certain threshold
    # and haven't been notified yet, to avoid spamming them with immediate notifications.
    cutoff = timezone.now() - timezone.timedelta(
        minutes=settings.EMAIL_NOTIFICATION_THRESHOLD_MINUTES
    )

    unread_struct = (
        ChatMessage.objects.filter(
            read_at__isnull=True, notified_at__isnull=True, timestamp__lt=cutoff
        )
        .annotate(
            recipient_id=Case(
                When(
                    sender=F("chat_request__user"), then=F("chat_request__ride__driver")
                ),
                default=F("chat_request__user"),
                output_field=UUIDField(),
            ),
            contact=F("sender__username"),
        )
        .filter(
            recipient_id__in=User.objects.filter(
                notification_preferences__unread_messages_notification=True
            ).values_list("pk", flat=True)
        )
        .values(
            "contact",  # contact
            "recipient_id",  # recipient
            "chat_request_id",
            "chat_request__ride__end_loc__city",  # ride_end
            "chat_request__ride__end_dt",  # ride_date
            "chat_request__user__username",  # passenger
            "chat_request__ride__driver__username",  # driver
        )
        .annotate(unread_count=Count("id"))
    )

    chats_by_user = defaultdict(list)

    for row in unread_struct:
        chats_by_user[row["recipient_id"]].append(
            {
                "chat_request_id": row["chat_request_id"],
                "ride_end": row["chat_request__ride__end_loc__city"],
                "ride_date": row["chat_request__ride__end_dt"],
                "passenger": row["chat_request__user__username"],
                "driver": row["chat_request__ride__driver__username"],
                "unread_count": row["unread_count"],
                "contact": row["contact"],
            }
        )

    for user_id, chats in chats_by_user.items():
        user = User.objects.get(pk=user_id)

        context = {
            "user": user,
            "unread_count": sum(chat["unread_count"] for chat in chats),
            "chats": chats,
        }

        message = render_to_string("chat/emails/unread_messages.txt", context)
        email = EmailMessage(
            subject="[INSAROULE]" + _("You have unread messages"),
            body=message,
            to=[user.email],
        )

        email.send(fail_silently=False)

        logger.info(f"Sent email to {user.email} about {len(chats)} chats.")

        # Update the notified_at timestamp for the messages that were included in the email
        ChatMessage.objects.filter(
            chat_request__uuid__in=[c["chat_request_id"] for c in chats],
            read_at__isnull=True,
            notified_at__isnull=True,
        ).update(notified_at=timezone.now())
