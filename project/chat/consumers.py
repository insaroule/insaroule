import json
import logging

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

logger = logging.getLogger(__name__)


def serialize_message(message, is_moderator=False):
    return {
        "type": "chat.message",
        "id": message.id,
        "content": (
            message.content
            if not message.hidden or is_moderator
            else "This message has been removed."
        ),
        "timestamp": message.timestamp.isoformat(),
        "user_uuid": str(message.sender.uuid),
        "hidden": message.hidden,
    }


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.room_id = self.scope["url_route"]["kwargs"]["jr_pk"]
        self.room_group_name = f"chat_{self.room_id}"

        self.chat_request = await self._get_chat_request()
        if not self.chat_request:
            logger.warning(
                f"ChatRequest with id {self.room_id} not found. Closing connection."
            )
            await self.close()
            return

        self.is_moderator = await sync_to_async(self.user.has_perm)(
            "chat.can_moderate_messages"
        )

        if not await self._has_access():
            logger.warning(
                f"User {self.user} does not have access to chat {self.room_id}. Closing connection."
            )
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        await self._send_previous_messages()

    async def disconnect(self, close_code):
        logger.debug(
            f"User {self.user} disconnected from chat {self.room_id} with code {close_code}"
        )
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)

        if "message" in data:
            await self._handle_new_message(data["message"])

        elif "action" in data:
            await self._handle_action(data)

    async def chat_message(self, event):
        """Broadcast message to client"""
        await self.send(text_data=json.dumps(event["payload"]))

    async def chat_action(self, event):
        await self.send(text_data=json.dumps(event))

    async def _handle_new_message(self, content):
        from chat.models import ChatMessage

        if len(content.strip()) > 1000:
            return

        message = await ChatMessage.objects.acreate(
            chat_request=self.chat_request,
            sender=self.user,
            content=content,
            timestamp=timezone.now(),
        )

        payload = serialize_message(message)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat.message",
                "payload": payload,
            },
        )

    async def _handle_action(self, data):
        from chat.models import ChatMessage

        action = data.get("action")
        message_id = data.get("message_id")

        if action in ["hide", "unhide"] and message_id:
            if not self.is_moderator:
                logger.warning(
                    f"User {self.user} attempted to perform action '{action}' on message {message_id} without permission"
                )
                return

            await sync_to_async(ChatMessage.objects.filter(pk=message_id).update)(
                hidden=(action == "hide")
            )

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat.action",
                    "action": action,
                    "message_id": message_id,
                },
            )

        elif action == "mark_read":
            await sync_to_async(
                ChatMessage.objects.filter(
                    chat_request=self.chat_request,
                    read_at__isnull=True,
                )
                .exclude(sender=self.user)
                .update
            )(read_at=timezone.now())
            logger.debug(
                f"User {self.user} marked messages as read in chat {self.room_id}"
            )

    async def _get_chat_request(self):
        from chat.models import ChatRequest

        qs = ChatRequest.objects.filter(pk=self.room_id)
        if not await qs.aexists():
            logger.error(f"ChatRequest {self.room_id} does not exist")
            return None
        return await qs.afirst()

    async def _has_access(self):
        if self.user.is_anonymous:
            logger.debug(f"Anonymous user attempted to access chat {self.room_id}")
            return False

        is_participant = await sync_to_async(
            lambda: self.user in [self.chat_request.user, self.chat_request.ride.driver]
        )()

        logger.debug(
            f"User {self.user} access check for chat {self.room_id}: is_participant={is_participant}, is_moderator={self.is_moderator}"
        )
        return is_participant or self.is_moderator

    async def _send_previous_messages(self):
        from chat.models import ChatMessage

        messages = await sync_to_async(list)(
            ChatMessage.objects.filter(chat_request=self.chat_request)
            .select_related("sender")
            .order_by("timestamp")[:50]
        )

        logger.debug(
            f"Sending {len(messages)} previous messages to user {self.user} for chat {self.room_id}"
        )

        for msg in messages:
            payload = serialize_message(msg, self.is_moderator)
            await self.send(text_data=json.dumps(payload))
