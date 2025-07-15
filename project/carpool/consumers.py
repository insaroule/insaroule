import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone
from asgiref.sync import sync_to_async


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        from carpool.models import ChatMessages, JoinRequest

        self.user = self.scope["user"]
        self.room_name = self.scope["url_route"]["kwargs"]["jr_pk"]
        self.room_group_name = f"chat_{self.room_name}"

        # Fetch the JoinRequest instance
        self.join_request = await sync_to_async(JoinRequest.objects.get)(
            pk=self.room_name
        )

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        previous_messages = await sync_to_async(list)(
            ChatMessages.objects.filter(join_request=self.join_request)
            .select_related("sender")
            .order_by("timestamp")[:50]
            .values("sender__username", "content", "timestamp")
        )

        for msg in previous_messages:
            direction = "out" if msg["sender__username"] == self.user.username else "in"
            await self.send(
                text_data=json.dumps(
                    {
                        "message": msg["content"],
                        "timestamp": msg["timestamp"].isoformat(),
                        "dir": direction,
                    }
                )
            )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        from carpool.models import ChatMessages

        text_data_json = json.loads(text_data)
        message = text_data_json["message"]
        timestamp = timezone.now()

        await ChatMessages.objects.acreate(
            join_request=self.join_request,
            sender=self.user,
            content=message,
            timestamp=timestamp,
        )

        data = {
            "type": "chat.message",
            "message": message,
            "timestamp": timestamp.isoformat(),
            "sender": self.user.username,
        }

        await self.channel_layer.group_send(self.room_group_name, data)

    async def chat_message(self, event):
        message = event["message"]
        timestamp = event["timestamp"]
        sender = event["sender"]

        direction = "out" if sender == self.user.username else "in"

        await self.send(
            text_data=json.dumps(
                {
                    "message": message,
                    "timestamp": timestamp,
                    "dir": direction,
                }
            )
        )
