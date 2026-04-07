from chat.api.serializers import ChatRequestSerializer
from rest_framework import viewsets, permissions
from chat.models import ChatRequest


class ChatRequestViewSet(viewsets.ModelViewSet):
    queryset = ChatRequest.objects.all()
    serializer_class = ChatRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
