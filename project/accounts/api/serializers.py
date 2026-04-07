from rest_framework import serializers
from accounts.models import User


class UsernameUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["uuid", "username"]
