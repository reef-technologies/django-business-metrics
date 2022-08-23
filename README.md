# Django Prometheus business metrics

This Django app provides a Prometheus metrics endpoint serving so-called business metrics. These are metrics that are calculated when Prometheus hits the metrics endpoint.

## Usage

1. Create a `BusinessMetricsManager` object and register some metrics:

    ```
    # project/business_metrics.py

    from django_business_metrics.v0 import BusinessMetricsManager, users, HistogramOutput

    metrics_manager = BusinessMetricsManager()

    # Add a pre-defined metric
    metrics_manager.add(users)

    # Add a custom gauge metric
    @metrics_manager.metric(name='my_gauge', documentation='documentation')
    def my_gauge():
        return 10

    # Add a custom histogram metric
    @metrics_manager.metric(name='my_histogram')
    def my_histogram():
        return HistogramOutput(
            sum_value=1000,
            buckets={'0.01': 1, '0.1': 10, '1': 10, '+Inf': 100}
        )
    ```

2. Register a Prometheus endpoint:


    ```
    # project/urls.py

    ...
    from .business_metrics import metrics_manager

    ...
    urlpatterns = [
        ...
        path('business-metrics', metrics_manager.view),
        ...
    ]
    ```

3. Setup your Prometheus agent to scrape metrics from `/business-metrics` endpoint.