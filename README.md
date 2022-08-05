# Django Prometheus business metrics

# Usage

1. Register a business metrics endpoint in your Django project's `urls.py`:

    ```
    from django_business_metrics.v0 import business_metrics_view

    ...
    urlpatterns = [
        ...
        path(r'business_metrics/?', business_metrics_view),
        ...
    ]
    ```

2. Register some custom metrics:

    ```
    from django.contrib.auth.models import User
    from django_business_metrics.v0 import business_metrics

    @business_metrics(name="user_count")
    def user_count():
        return User.objects.count()
    ```

    And/or register some of the pre-defined metrics:

    ```
    from django_business_metrics.v0 import BUSINESS_METRICS_COLLECTOR, user_count_metric

    BUSINESS_METRICS_COLLECTOR.register_metric(
        name="user_count",
        callable=user_count_metric
    )
    ```

3. Setup your Prometheus agent to scrape metrics from `/business_metrics` endpoint.