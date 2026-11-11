from rest_framework.test import APIClient

from apps.accounts.models import User

V1 = "/api/v1"


def client_for(email="student@example.com", role=None, plan=None, language=None):
    c = APIClient()
    r = c.post(f"{V1}/auth/dev-login/", {"email": email}, format="json")
    assert r.status_code == 200, r.content
    updates = {k: v for k, v in {"role": role, "plan": plan, "ui_language": language}.items() if v}
    if updates:
        User.objects.filter(email=email).update(**updates)
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
    return c
