import os

import pytest

from content_gen.core.metrics import (
    FileMetricsTracker,
    MemoryMetricsTracker,
    create_metrics_tracker,
)


def test_create_metrics_memory(monkeypatch):
    monkeypatch.setenv("EDMATE_METRICS_BACKEND", "memory")
    t = create_metrics_tracker()
    assert isinstance(t, MemoryMetricsTracker)


def test_create_metrics_file_default(monkeypatch, tmp_path):
    monkeypatch.delenv("EDMATE_METRICS_BACKEND", raising=False)
    f = tmp_path / "m.json"
    monkeypatch.setenv("EDMATE_METRICS_FILE", str(f))
    t = create_metrics_tracker()
    assert isinstance(t, FileMetricsTracker)


@pytest.mark.skipif(not os.environ.get("RUN_REDIS_METRICS_TEST"), reason="set RUN_REDIS_METRICS_TEST=1 to run")
def test_create_metrics_redis_integration(monkeypatch):
    url = os.environ["EDMATE_METRICS_REDIS_URL"]
    monkeypatch.setenv("EDMATE_METRICS_BACKEND", "redis")
    monkeypatch.setenv("EDMATE_METRICS_REDIS_URL", url)
    pytest.importorskip("redis")
    t = create_metrics_tracker()
    assert t.get_current_cost() >= 0.0
