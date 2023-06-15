# Django Prometheus business metrics

This Django app provides a Prometheus metrics endpoint serving so-called business metrics. These are metrics that are calculated when Prometheus hits the metrics endpoint.

## Usage

> This project uses [ApiVer](https://www.youtube.com/watch?v=FgcoAKchPjk).
> Always import from `django_business_metrics.v0` namespace and not from `django_business_metrics`.


1. Create a `BusinessMetricsManager` object and register some metrics:

    ```
    # project/business_metrics.py

    from django_business_metrics.v0 import BusinessMetricsManager, users

    metrics_manager = BusinessMetricsManager()

    # Add a pre-defined metric
    metrics_manager.add(users)

    # Add some custom metrics
    @metrics_manager.metric(name='name', documentation='documentation')
    def my_metric():
        return 10
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


## Development

```
poetry install
```

Before committing make sure to run:

```
nox -s format test
```