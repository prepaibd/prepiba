from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .serializers import UserSerializer


def verify_google_token(token: str) -> dict:
    """Return the verified Google claims, or raise ValueError. Isolated so tests can patch it."""
    if not settings.GOOGLE_CLIENT_ID:
        raise ValueError("Google login is not configured")
    return google_id_token.verify_oauth2_token(token, google_requests.Request(), settings.GOOGLE_CLIENT_ID)


def issue_tokens(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh), "user": UserSerializer(user).data}


class _TokenIn(serializers.Serializer):
    id_token = serializers.CharField()


class GoogleLoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        data = _TokenIn(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            claims = verify_google_token(data.validated_data["id_token"])
        except ValueError:
            return Response({"detail": "Invalid Google token"}, status=status.HTTP_401_UNAUTHORIZED)
        if not claims.get("email_verified") or not claims.get("email"):
            return Response({"detail": "Google email is not verified"}, status=status.HTTP_401_UNAUTHORIZED)
        email = claims["email"].lower()
        user = User.objects.filter(google_sub=claims["sub"]).first() or User.objects.filter(email=email).first()
        if user is None:
            user = User.objects.create_user(email=email, google_sub=claims["sub"], name=claims.get("name", ""),
                                            avatar_url=claims.get("picture", ""))
        elif not user.google_sub:
            user.google_sub = claims["sub"]
            user.save(update_fields=["google_sub"])
        if not user.is_active:
            return Response({"detail": "Account disabled"}, status=status.HTTP_403_FORBIDDEN)
        return Response(issue_tokens(user))


class _DevIn(serializers.Serializer):
    email = serializers.EmailField()


class DevLoginView(APIView):
    """Email-only login for local development. 404s unless settings.DEV_LOGIN_ENABLED."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        if not settings.DEV_LOGIN_ENABLED:
            return Response(status=status.HTTP_404_NOT_FOUND)
        data = _DevIn(data=request.data)
        data.is_valid(raise_exception=True)
        email = data.validated_data["email"].lower()
        user, _ = User.objects.get_or_create(email=email, defaults={"name": email.split("@")[0]})
        return Response(issue_tokens(user))


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        ser = UserSerializer(request.user, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)
