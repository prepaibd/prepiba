import time

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.ai import prompts, quota
from apps.ai.provider import ProviderError, get_provider
from apps.catalog.models import Question

from . import feedback
from .models import WritingSubmission
from .serializers import PromptSerializer, SubmissionCreateSerializer, SubmissionSerializer, words


class PromptViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PromptSerializer
    pagination_class = None

    def get_queryset(self):
        return (Question.objects.filter(type__in=["essay", "argument"]).select_related("section__exam", "group")
                .order_by("-section__exam__year", "-section__exam__month", "number"))


def grade(user, submission: WritingSubmission) -> tuple[bool, Response | None]:
    """Run the model on a submission. Returns (ok, error_response). Charges the allowance only on success."""
    try:
        provider = get_provider()
    except ProviderError:
        return False, Response({"detail": "Writing feedback is not available right now."},
                               status=status.HTTP_503_SERVICE_UNAVAILABLE)
    try:
        usage = quota.reserve(user, "writing", provider.model)
    except quota.QuotaExceeded as e:
        return False, Response({"detail": f"You have used all {e.limit} writing reviews for today.",
                                "limit": e.limit, "resets_at": e.resets_at}, status=status.HTTP_429_TOO_MANY_REQUESTS)

    q = submission.prompt
    system = prompts.WRITING_SYSTEM.format(language=prompts.LANGUAGES[user.ui_language])
    task = "argument analysis" if q.type == "argument" else "essay"
    prompt = (f"TASK TYPE: {task}\n<<<TASK\n{q.group.instruction + chr(10) if q.group and q.group.instruction else ''}"
              f"{q.stem}\nTASK>>>\n\n<<<STUDENT TEXT\n{submission.body}\nSTUDENT TEXT>>>")
    result, error = None, "provider error"
    started = time.monotonic()
    for attempt in range(2):  # one retry if the model returns unusable JSON, if the time budget allows
        if attempt and time.monotonic() - started >= settings.AI_TIMEOUT_SECONDS:
            break
        try:
            result = feedback.normalise(provider.generate_json(system, prompt), submission.body)
            break
        except ProviderError:
            error = "provider error"
            break
        except ValueError:
            error = "unusable model output"
    if result is None:
        quota.release(usage, error)
        submission.status, submission.error, submission.feedback = WritingSubmission.Status.FAILED, error, None
        submission.save(update_fields=["status", "error", "feedback", "updated_at"])
        return False, Response({"detail": "We could not review this right now. Your text is saved; try again.",
                                "submission": SubmissionSerializer(submission).data},
                               status=status.HTTP_502_BAD_GATEWAY)
    quota.complete(usage, len(prompt), len(str(result)))
    submission.status, submission.error, submission.feedback = WritingSubmission.Status.DONE, "", result
    submission.model = provider.model
    submission.save(update_fields=["status", "error", "feedback", "model", "updated_at"])
    return True, None


class SubmissionViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    serializer_class = SubmissionSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "writing"

    def get_queryset(self):
        return WritingSubmission.objects.filter(user=self.request.user).select_related(
            "prompt__section__exam", "prompt__group")

    def create(self, request, *args, **kwargs):
        ser = SubmissionCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        sub = WritingSubmission.objects.create(user=request.user, prompt=d["question"], body=d["body"],
                                               word_count=words(d["body"]))
        ok, err = grade(request.user, sub)
        if not ok:
            return err
        return Response(SubmissionSerializer(self.get_queryset().get(pk=sub.pk)).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        sub = get_object_or_404(self.get_queryset(), pk=pk)
        if sub.status != WritingSubmission.Status.FAILED:
            return Response({"detail": "This submission already has feedback."}, status=status.HTTP_409_CONFLICT)
        ok, err = grade(request.user, sub)
        return err if not ok else Response(SubmissionSerializer(self.get_queryset().get(pk=sub.pk)).data)
