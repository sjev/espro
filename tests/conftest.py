from __future__ import annotations

import pytest

from espro.config import get_settings


@pytest.fixture(autouse=True)
def _isolate_settings_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("ESPRO_CONFIG", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
