from django.contrib import admin
from chat.models import ChatMessage, ChatRequest

admin.site.register(ChatMessage)
admin.site.register(ChatRequest)
