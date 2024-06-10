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

Pre-requisites:
- [pdm](https://pdm.fming.dev/)
- [nox](https://nox.thea.codes/en/stable/)
- [docker](https://www.docker.com/) and [docker composep plugin](https://docs.docker.com/compose/)


Ideally, you should run `nox -t format lint` before every commit to ensure that the code is properly formatted and linted.
Before submitting a PR, make sure that tests pass as well, you can do so using:
```
nox -t check # equivalent to `nox -t format lint test`
```

If you wish to install dependencies into `.venv` so your IDE can pick them up, you can do so using:
```
pdm install --dev
```

### Release process

Run `nox -s make_release -- X.Y.Z` where `X.Y.Z` is the version you're releasing and follow the printed instructions.
