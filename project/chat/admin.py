from django.contrib import admin
from chat.models import ChatMessage, ChatRequest, ChatReport, ModAction

admin.site.register(ChatRequest)
admin.site.register(ChatReport)
admin.site.register(ModAction)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("sender", "chat_request", "timestamp")
    search_fields = ("content",)
    list_filter = ("sender", "chat_request", "timestamp")
    ordering = ("-timestamp",)
