"""Per-user daily AI allowance by plan. The allowance is reserved *before* the model is called, under a row lock
on the user, so concurrent requests cannot overshoot the limit; failed calls are released."""
from dataclasses import dataclass
from datetime import datetime, time, timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User

from .models import AIUsageLog


class QuotaExceeded(Exception):
    def __init__(self, kind: str, limit: int, resets_at: datetime):
        self.kind, self.limit, self.resets_at = kind, limit, resets_at
        super().__init__(f"Daily {kind} limit of {limit} reached")


@dataclass
class Allowance:
    kind: str
    used: int
    limit: int
    resets_at: datetime

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.used)


def day_window(now: datetime | None = None) -> tuple[datetime, datetime]:
    now = timezone.localtime(now or timezone.now())
    start = timezone.make_aware(datetime.combine(now.date(), time.min), timezone.get_current_timezone())
    return start, start + timedelta(days=1)


def limit_for(user: User, kind: str) -> int:
    return settings.AI_DAILY_LIMITS[user.plan][kind]


def allowance(user: User, kind: str) -> Allowance:
    start, end = day_window()
    used = AIUsageLog.objects.filter(user=user, kind=kind, status=AIUsageLog.Status.OK, created_at__gte=start).count()
    return Allowance(kind, used, limit_for(user, kind), end)


def reserve(user: User, kind: str, model: str = "") -> AIUsageLog:
    with transaction.atomic():
        User.objects.select_for_update().get(pk=user.pk)  # serialise this user's reservations
        a = allowance(user, kind)
        if a.remaining <= 0:
            raise QuotaExceeded(kind, a.limit, a.resets_at)
        return AIUsageLog.objects.create(user=user, kind=kind, model=model)


def complete(log: AIUsageLog, prompt_chars: int, output_chars: int):
    log.prompt_chars, log.output_chars = prompt_chars, output_chars
    log.save(update_fields=["prompt_chars", "output_chars", "updated_at"])


def release(log: AIUsageLog, error: str):
    """The call failed: do not charge the user for it."""
    log.status, log.error = AIUsageLog.Status.ERROR, error[:300]
    log.save(update_fields=["status", "error", "updated_at"])
