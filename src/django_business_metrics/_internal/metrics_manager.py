from __future__ import annotations

import logging
import time
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from typing import Callable

import prometheus_client
from django.http import HttpRequest, HttpResponse
from prometheus_client.metrics_core import GaugeMetricFamily
from prometheus_client.registry import CollectorRegistry

logger = logging.getLogger(__name__)


@dataclass
class _BusinessMetric:
    name: str
    documentation: str
    callable: Callable[[], float]


class _BusinessMetricsCollector(CollectorRegistry):
    _metrics: dict[str, _BusinessMetric]
    _concurrent_collections: int
    _timeout: float

    def __init__(self, concurrent_collections: int, timeout: float):
        self._metrics = {}
        self._concurrent_collections = concurrent_collections
        self._timeout = timeout

    @staticmethod
    def _map_metric(metric: _BusinessMetric) -> GaugeMetricFamily:
        return GaugeMetricFamily(
            name=metric.name,
            documentation=metric.documentation,
            value=metric.callable(),
        )

    def add(self, metric: _BusinessMetric):
        if metric.name in self._metrics:
            raise ValueError(f"Business metric with name {metric.name} already exists")
        self._metrics[metric.name] = metric
        return self

    def collect(self) -> Iterable[GaugeMetricFamily]:
        """
        Collect every metric, bounded by ``timeout``, without one failure hiding the rest.

        ``pool.map`` is lazy: its ``timeout`` applies while the caller iterates the result.
        Returning that generator from inside ``with ThreadPoolExecutor(...)`` meant the
        block's ``__exit__`` ran ``shutdown(wait=True)`` first, which waits for every future
        with no timeout at all. By the time anything iterated, the work had already finished,
        so the documented timeout could never fire and a slow metric hung the scrape
        indefinitely.

        Iterating outside the block also surfaced a failing metric inside
        ``prometheus_client.generate_latest()`` rather than here, and took the whole scrape
        with it: metrics after the failing one were never emitted.
        """
        pool = ThreadPoolExecutor(max_workers=self._concurrent_collections)
        try:
            futures = {metric.name: pool.submit(self._map_metric, metric) for metric in self._metrics.values()}
            deadline = time.monotonic() + self._timeout
            collected = []
            for name, future in futures.items():
                remaining = deadline - time.monotonic()
                try:
                    collected.append(future.result(timeout=max(remaining, 0)))
                except FuturesTimeoutError:
                    logger.warning("Business metric %r timed out after %ss; skipping it.", name, self._timeout)
                except Exception:
                    # One bad query must not delete every other metric from the scrape.
                    logger.exception("Business metric %r raised; skipping it.", name)
            return collected
        finally:
            # Do not block the response on metrics that already missed the deadline.
            pool.shutdown(wait=False)


class BusinessMetricsManager:
    """BusinessMetricsManager collects and formats business metrics."""

    _collector: _BusinessMetricsCollector

    def __init__(self, concurrent_collections: int = 5, timeout=10):
        """
        concurrent_collections - how many metrics should be collected concurrently at a time.
        timeout - timeout of the metrics collection.
        """
        self._collector = _BusinessMetricsCollector(concurrent_collections, timeout)

    def add(self, callable: Callable[[], float], name=None, documentation=""):
        """Add a metric."""
        metric = _BusinessMetric(
            name=name or callable.__name__,
            documentation=documentation,
            callable=callable,
        )
        self._collector.add(metric)
        return self

    def metric(self, name: str | None = None, documentation: str = "") -> Callable:
        """
        A decorator that marks a function as a metric.

        Example use::

           @metric_manager.metric(name='my_metric_name', documentation='My documentation')
           def my_metric():
               return 1

        :param name: name of the metric. If not provided, the function name will be used.
        :param documentation: description of the metric.
        """

        def metric_decorator(callable: Callable[[], float]):
            self.add(callable, name or callable.__name__, documentation=documentation)
            return callable

        return metric_decorator

    def view(self, _: HttpRequest) -> HttpResponse:
        """Django view that returns a Prometheus-compatable metrics scrape page."""
        return HttpResponse(
            prometheus_client.generate_latest(self._collector),
            content_type=prometheus_client.CONTENT_TYPE_LATEST,
        )
