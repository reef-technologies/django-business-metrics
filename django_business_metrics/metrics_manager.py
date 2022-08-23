from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Optional, Union

import prometheus_client
from django.http import HttpRequest, HttpResponse
from prometheus_client.metrics_core import GaugeMetricFamily, HistogramMetricFamily
from prometheus_client.registry import CollectorRegistry


@dataclass
class HistogramOutput:
    sum_value: float
    """Sum value of all observatons."""

    buckets: Dict[str, int]
    """A dict of `upper_bound: count` pairs where `count` is a number
    of _all_ observations that are less than or equal to `upper_bound`.
    For example, observation with value 0.1 should be counted in all
    buckets with label higher or equal to 0.1: '0.1', '0.2', etc.

    There must be at least two buckets.
    There must be a special bucket with key '+Inf' which contains the
    count of all observations.
    All bucket keys must be string representations of float numbers.

    Example:
    ```{'0.1': 1, '1': 10, '+Inf': 100}```
    """


MetricOutput = Union[float, HistogramOutput]
"""Metric output type."""

MetricCallable = Callable[[], MetricOutput]
"""A type of a callable that can be registered as a metric."""

_MetricFamily = Union[GaugeMetricFamily, HistogramMetricFamily]


@dataclass
class _BusinessMetric:
    name: str
    documentation: str
    callable: MetricCallable


class _BusinessMetricsCollector(CollectorRegistry):
    _metrics: Dict[str, _BusinessMetric]
    _concurrent_collections: int
    _timeout: float

    def __init__(self, concurrent_collections: int, timeout: float):
        self._metrics = {}
        self._concurrent_collections = concurrent_collections
        self._timeout = timeout

    @staticmethod
    def _map_metric(metric: _BusinessMetric) -> _MetricFamily:
        value = metric.callable()
        if isinstance(value, float) or isinstance(value, int):
            return GaugeMetricFamily(
                name=metric.name,
                documentation=metric.documentation,
                value=value,
            )
        elif isinstance(value, HistogramOutput):
            buckets = list(value.buckets.items())
            buckets.sort(key=lambda item: float(item[0]))
            if len(buckets) < 2:
                raise ValueError("There must be at least two buckets")
            if buckets[-1][0] != "+Inf":
                raise ValueError("There must be an '+Inf' bucket")
            return HistogramMetricFamily(
                name=metric.name,
                documentation=metric.documentation,
                sum_value=value.sum_value,
                buckets=buckets,
            )
        else:
            raise ValueError("Metric must return either float or HistogramOutput")

    def add(self, metric: _BusinessMetric):
        if metric.name in self._metrics:
            raise ValueError(f"Business metric with name {metric.name} already exists")
        self._metrics[metric.name] = metric
        return self

    def collect(self) -> Iterable[_MetricFamily]:
        with ThreadPoolExecutor(max_workers=self._concurrent_collections) as pool:
            return pool.map(
                self._map_metric, self._metrics.values(), timeout=self._timeout
            )


class BusinessMetricsManager:
    """BusinessMetricsManager collects and formats business metrics."""

    _collector: _BusinessMetricsCollector

    def __init__(self, concurrent_collections: int = 5, timeout=10):
        """
        concurrent_collections - how many metrics should be collected concurrently at a time.
        timeout - timeout of the metrics collection.
        """
        self._collector = _BusinessMetricsCollector(concurrent_collections, timeout)

    def add(self, callable: MetricCallable, name=None, documentation=""):
        """Add a metric."""
        metric = _BusinessMetric(
            name=name or callable.__name__,
            documentation=documentation,
            callable=callable,
        )
        self._collector.add(metric)
        return self

    def metric(self, name: Optional[str] = None, documentation: str = ""):
        """A decorator that marks a function as a metric.

        Example use:
        ```
        @metric_manager.metric(name='my_metric_name', documentation='My documentation')
        def my_metric():
            return 1
        ```

        Parameters:
        name - name or the metric. If not provided, function name will be used.
        documentation - description of the metric. Optional.
        """

        def metric_decorator(callable: MetricCallable):
            self.add(callable, name or callable.__name__, documentation=documentation)
            return callable

        return metric_decorator

    def view(self, _: HttpRequest) -> HttpResponse:
        """Django view that returns a Prometheus-compatable metrics scrape page."""
        return HttpResponse(
            prometheus_client.generate_latest(self._collector),
            content_type=prometheus_client.CONTENT_TYPE_LATEST,
        )
