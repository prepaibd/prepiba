from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.practice import scoring
from apps.practice.models import Attempt


class Command(BaseCommand):
    help = "Auto-submit in-progress attempts whose deadline has passed (run periodically, e.g. every minute)."

    def handle(self, *args, **opts):
        n = 0
        for attempt in Attempt.objects.filter(status=Attempt.Status.IN_PROGRESS, deadline_at__lte=timezone.now()):
            scoring.finalize(attempt, Attempt.Status.EXPIRED)
            n += 1
        self.stdout.write(f"auto-submitted {n} attempt(s)")
