from django.contrib.auth.admin import UserAdmin
from django.contrib import admin
from accounts.models import User

admin.site.register(User, UserAdmin)
