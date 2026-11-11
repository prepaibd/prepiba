from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "name", "avatar_url", "role", "plan", "ui_language"]
        read_only_fields = ["id", "email", "avatar_url", "role", "plan"]
