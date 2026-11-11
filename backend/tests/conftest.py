import pytest

from apps.catalog.importer import import_all


@pytest.fixture(scope="session")
def media_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("media")


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker, media_dir):
    """Import the real curated data once; tests then read it inside rolled-back transactions."""
    from django.conf import settings

    settings.MEDIA_ROOT = media_dir
    with django_db_blocker.unblock():
        import_all()


@pytest.fixture(autouse=True)
def _media_root(settings, media_dir):
    settings.MEDIA_ROOT = media_dir


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    from django.core.cache import cache

    cache.clear()


@pytest.fixture(autouse=True)
def _never_call_a_real_model(settings):
    """Tests must be hermetic and free: whatever .env says, AI calls go to the mock provider and no key is set.
    Tests that exercise the Gemini adapter inject a fake client explicitly."""
    settings.AI_PROVIDER = "mock"
    settings.GEMINI_API_KEY = ""
