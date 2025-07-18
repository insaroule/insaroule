from django.contrib import admin
from chat.models import ChatMessage, ChatRequest, ChatReport

admin.site.register(ChatRequest)
admin.site.register(ChatReport)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("sender", "chat_request", "timestamp")
    search_fields = ("content",)
    list_filter = ("sender", "chat_request", "timestamp")
    ordering = ("-timestamp",)
