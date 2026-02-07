import sys
from pathlib import Path

import pytest

# Ensure project root is importable when pytest is invoked from non-root directories.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _force_stub_generator(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings

    # Keep API/UI tests deterministic regardless of caller shell environment.
    monkeypatch.setenv("RECIPE_GENERATOR", "stub")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()
