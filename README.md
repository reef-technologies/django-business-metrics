# Django Prometheus business metrics
&nbsp;[![Continuous Integration](https://github.com/reef-technologies/django-business-metrics/workflows/Continuous%20Integration/badge.svg)](https://github.com/reef-technologies/django-business-metrics/actions?query=workflow%3A%22Continuous+Integration%22)&nbsp;[![License](https://img.shields.io/pypi/l/django_business_metrics.svg?label=License)](https://pypi.python.org/pypi/django_business_metrics)&nbsp;[![python versions](https://img.shields.io/pypi/pyversions/django_business_metrics.svg?label=python%20versions)](https://pypi.python.org/pypi/django_business_metrics)&nbsp;[![PyPI version](https://img.shields.io/pypi/v/django_business_metrics.svg?label=PyPI%20version)](https://pypi.python.org/pypi/django_business_metrics)

This Django app provides a Prometheus metrics endpoint serving so-called business metrics. These are metrics that are calculated when Prometheus hits the metrics endpoint.

## Usage

> [!IMPORTANT]
> This package uses [ApiVer](#versioning), make sure to import `django_business_metrics.v0`.

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
- [uv](https://docs.astral.sh/uv/)
- [nox](https://nox.thea.codes/en/stable/) - may be installed as `uv tool install --with pyyaml --exclude-newer "14 days" nox`
- [docker](https://www.docker.com/) and [docker compose plugin](https://docs.docker.com/compose/)

Ideally, you should run `nox -s format lint` before every commit to ensure that the code is properly formatted and linted.
Before submitting a PR, make sure that tests pass as well, you can do so using:

```sh
nox -t check  # equivalent to `nox -s format lint test`
```

If you wish to install dependencies into `.venv` so your IDE can pick them up, you can do so using:

```sh
uv sync --all-extras --dev
```

### Python  / django  version compatibility

Use cruft questionnaire to add/remove supported versions: `cruft update --cookiecutter-input`

### Versioning

This package uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html) and [Conventional Commits](https://www.conventionalcommits.org/).

[Commitizen](https://commitizen-tools.github.io/commitizen/) may be used to generate commit messages:

```sh
uv tool install "commitizen==4.13.9"
git add ...
cz commit
```

Additionally, this package uses [ApiVer](https://www.youtube.com/watch?v=FgcoAKchPjk) to further reduce the risk of breaking changes.
This means, the public API of this package is explicitly versioned, e.g. `django_business_metrics.v1`, and will not change in a backwards-incompatible way even when `django_business_metrics.v2` is released.

Internal packages, i.e. prefixed by `django_business_metrics._` do not share these guarantees and may change in a backwards-incompatible way at any time even in patch releases.

### Release process

Releases are prepared explicitly *by developers* with help of Commitizen. Run `cz bump` which will:
- update the changelog
- make the bump commit and tag it

Then push the commit & tag to the repository, which will trigger the release workflow:
```sh
git push origin HEAD --follow-tags
```

- `alpha`, `beta` and `rc` releases are published to TestPyPI (use `cz bump --prerelease alpha|beta|rc` to create them)
- regular ones are published to PyPI
