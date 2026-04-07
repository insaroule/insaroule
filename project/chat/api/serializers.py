from chat.models import ChatRequest
from carpool.api.serializers import SmallRideSerializer
from accounts.api.serializers import UsernameUserSerializer
from rest_framework import serializers


class ChatRequestSerializer(serializers.ModelSerializer):
    user = UsernameUserSerializer(read_only=True)
    ride = SmallRideSerializer(read_only=True)

    class Meta:
        model = ChatRequest
        fields = ["uuid", "ride", "user", "created_at"]
