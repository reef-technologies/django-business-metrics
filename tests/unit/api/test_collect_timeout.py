"""
The documented ``timeout`` must actually bound collection, and one bad metric
must not delete every other metric from the scrape.

``pool.map`` is lazy: its ``timeout`` applies while the caller iterates the result.
Returning that generator from inside ``with ThreadPoolExecutor(...)`` meant the block's
``__exit__`` ran ``shutdown(wait=True)`` first, which waits for every future with no
timeout. By the time anything iterated, the work had already finished, so the timeout
could never fire.

Measured on the previous implementation: timeout=1, one metric sleeping 5 seconds,
``collect()`` returned after 5.00 seconds and raised nothing.
"""

import time

import pytest


@pytest.fixture
def manager(apiver_module):
    return apiver_module.BusinessMetricsManager


class TestCollectTimeout:
    def test_slow_metric_does_not_hang_the_scrape(self, manager):
        """A metric slower than the timeout is skipped, not waited on."""
        m = manager(concurrent_collections=5, timeout=0.5)
        m.add(lambda: 1, name="fast", documentation="")
        m.add(lambda: (time.sleep(5), 2)[1], name="slow", documentation="")

        started = time.monotonic()
        collected = list(m._collector.collect())
        elapsed = time.monotonic() - started

        assert elapsed < 3, f"collect() waited {elapsed:.2f}s despite a 0.5s timeout"
        names = {c.name for c in collected}
        assert "fast" in names, "the healthy metric must still be reported"
        assert "slow" not in names, "the timed-out metric must be omitted, not blocked on"

    def test_one_failing_metric_does_not_delete_the_others(self, manager):
        """
        A raising metric is skipped; the rest of the scrape survives.

        Previously the exception surfaced at iteration time inside
        prometheus_client.generate_latest(), which meant metrics registered after the
        failing one were never emitted at all.
        """
        m = manager(concurrent_collections=5, timeout=10)
        m.add(lambda: 1, name="before", documentation="")

        def broken():
            raise RuntimeError("one bad DB query")

        m.add(broken, name="broken", documentation="")
        m.add(lambda: 3, name="after", documentation="")

        collected = list(m._collector.collect())
        names = {c.name for c in collected}

        assert "before" in names
        assert "after" in names, "a metric registered after the failing one must still be emitted"
        assert "broken" not in names

    def test_all_healthy_metrics_are_unchanged(self, manager):
        """With nothing slow or broken, behaviour is exactly as before."""
        m = manager(concurrent_collections=5, timeout=10)
        m.add(lambda: 1, name="a", documentation="")
        m.add(lambda: 2, name="b", documentation="")

        collected = {c.name: c.samples[0].value for c in m._collector.collect()}
        assert collected == {"a": 1.0, "b": 2.0}

    def test_view_still_renders_when_a_metric_fails(self, request_factory, manager):
        """The scrape endpoint must return 200 with the surviving metrics."""
        m = manager(concurrent_collections=5, timeout=10)
        m.add(lambda: 7, name="healthy", documentation="")

        def broken():
            raise RuntimeError("boom")

        m.add(broken, name="broken", documentation="")

        response = m.view(request_factory.get("/business-metrics"))
        assert response.status_code == 200
        assert b"healthy 7.0" in response.content
