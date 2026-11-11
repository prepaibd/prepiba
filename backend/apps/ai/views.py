from rest_framework.response import Response
from rest_framework.views import APIView

from . import quota
from .models import AIUsageLog


class UsageView(APIView):
    def get(self, request):
        out = {}
        for kind in AIUsageLog.Kind.values:
            a = quota.allowance(request.user, kind)
            out[kind] = {"used": a.used, "limit": a.limit, "remaining": a.remaining, "resets_at": a.resets_at}
        return Response(out)
