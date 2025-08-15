import json
import os
from contextlib import contextmanager

from moto.cloudwatch.models import MetricDatum
from moto.core.common_models import CloudWatchMetricProvider


@contextmanager
def temp_config(config: dict):
    os.environ["SCRAPE_CONFIG"] = json.dumps(config)
    yield
    os.environ.pop("SCRAPE_CONFIG", None)


_METRICS: list[MetricDatum] = []


class MetricsProvider(CloudWatchMetricProvider):

    @staticmethod
    def get_cloudwatch_metrics(account_id: str, region: str):

        return _METRICS


@contextmanager
def temp_metrics(metrics: list[MetricDatum]):
    _METRICS.extend(metrics)
    yield
    _METRICS.clear()
