import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone
from asgiref.sync import sync_to_async


class ChatConsumer(AsyncWebsocketConsumer):
    # TODO: simplify the logic by using external functions for permission checks and message retrieval
    async def connect(self):
        from chat.models import ChatMessage, ChatRequest

        self.user = self.scope["user"]
        self.room_name = self.scope["url_route"]["kwargs"]["jr_pk"]
        self.room_group_name = f"chat_{self.room_name}"

        self.chat_request = await sync_to_async(ChatRequest.objects.get)(
            pk=self.room_name
        )

        is_participant = await sync_to_async(
            lambda: self.user in [self.chat_request.user, self.chat_request.ride.driver]
        )()

        is_moderator = await sync_to_async(self.user.has_perm)(
            "chat.can_moderate_messages"
        )

        if self.user.is_anonymous or not is_participant and not is_moderator:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Send previous messages with user UUIDs
        previous_messages = await sync_to_async(list)(
            ChatMessage.objects.filter(chat_request=self.chat_request)
            .select_related("sender")
            .order_by("timestamp")[:50]
            .values("pk", "sender__uuid", "content", "timestamp", "hidden")
        )

        for message in previous_messages:
            # if user is not a moderator, hide the content of hidden messages
            if is_moderator:
                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "chat.message",
                            "id": message["pk"],
                            "message": message["content"],
                            "timestamp": message["timestamp"].isoformat(),
                            "user_uuid": str(message["sender__uuid"]),
                            "hidden": message["hidden"],
                        }
                    )
                )
            else:
                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "chat.message",
                            "id": message["pk"],
                            "message": "This message has been removed."
                            if message["hidden"]
                            else message["content"],
                            "timestamp": message["timestamp"].isoformat(),
                            "user_uuid": str(message["sender__uuid"]),
                            "hidden": message["hidden"],
                        }
                    )
                )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        """
        Handle incoming messages from the WebSocket.
        This method processes the received message, saves it to the database,
        and broadcasts it to the chat room.
        """

        from chat.models import ChatMessage

        text_data = json.loads(text_data)
        if "message" in text_data:
            message = text_data["message"]
            timestamp = timezone.now()

            await ChatMessage.objects.acreate(
                chat_request=self.chat_request,
                sender=self.user,
                content=message,
                timestamp=timestamp,
            )

            # Broadcast the message with user UUID
            data = {
                "type": "chat.message",
                "message": message,
                "timestamp": timestamp.isoformat(),
                "user_uuid": str(self.user.uuid),
            }

            await self.channel_layer.group_send(self.room_group_name, data)

        elif "action" in text_data:
            if not self.user.has_perm("chat.can_moderate_messages"):
                logging.warning(
                    f"User {self.user.username} attempted to perform moderation action without permission."
                )
                return
            action = text_data["action"]
            message_id = text_data.get("message_id")

            if action == "hide" and message_id:
                # Hide the message
                _ = await sync_to_async(
                    ChatMessage.objects.filter(pk=message_id).update
                )(hidden=True)

                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "chat.action",
                        "action": "hide",
                        "message_id": message_id,
                    },
                )

            elif action == "unhide" and message_id:
                _ = await sync_to_async(
                    ChatMessage.objects.filter(pk=message_id).update
                )(hidden=False)

                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "chat.action",
                        "action": "unhide",
                        "message_id": message_id,
                    },
                )

    async def chat_message(self, event):
        """
        Handler for type 'chat.message'.
        """
        message = event["message"]
        timestamp = event["timestamp"]
        user_uuid = event["user_uuid"]

        await self.send(
            text_data=json.dumps(
                {
                    "type": "chat.message",
                    "message_id": event.get("message_id"),
                    "message": message,
                    "timestamp": timestamp,
                    "user_uuid": user_uuid,
                }
            )
        )

    async def chat_action(self, event):
        """
        Handle chat actions such as hiding or unhiding messages.
        """
        action = event["action"]
        message_id = event["message_id"]

        await self.send(
            text_data=json.dumps(
                {
                    "type": "chat.action",
                    "action": action,
                    "message_id": message_id,
                }
            )
        )
