import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create(self, email, password, **extra):
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password) if password else user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.update(is_staff=True, is_superuser=True, role=User.Role.ADMIN)
        return self._create(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        STUDENT = "student"
        REVIEWER = "reviewer"
        ADMIN = "admin"

    class Plan(models.TextChoices):
        FREE = "free"
        PAID = "paid"

    class Language(models.TextChoices):
        EN = "en"
        BN = "bn"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    google_sub = models.CharField(max_length=64, unique=True, null=True, blank=True)
    name = models.CharField(max_length=150, blank=True)
    avatar_url = models.URLField(blank=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)
    plan = models.CharField(max_length=10, choices=Plan.choices, default=Plan.FREE)
    ui_language = models.CharField(max_length=2, choices=Language.choices, default=Language.EN)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    def __str__(self):
        return self.email
