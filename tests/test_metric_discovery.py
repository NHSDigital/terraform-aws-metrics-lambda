from datetime import UTC, datetime

import pytest
from botocore.config import Config
from clients import ClientFactory, SQSClient
from common import temp_config, temp_metrics
from config import ScrapeConfig
from executor import Executor
from moto.cloudwatch.models import MetricDatum


@pytest.mark.parametrize(
    ("dim_requirements", "expected"),
    [
        ({}, 2),
        ({"BucketName": "^temp-.*"}, 2),
        ({"BucketName": "bad"}, 0),
    ],
)
async def test_s3_discovery_search_dimensions(
    test_bucket, temp_queue, dim_requirements: dict, expected: int
):

    conf = {
        "discovery": {
            "jobs": [
                {
                    "type": "s3",
                    "regions": ["eu-west-2"],
                    "search_dimensions": dim_requirements,
                    "metrics": [
                        {
                            "name": "NumberOfObjects",
                            "stats": ["Average"],
                            "period": 86400,
                        },
                        {
                            "name": "BucketSizeBytes",
                            "stats": ["Average"],
                            "period": 86400,
                        },
                    ],
                }
            ]
        }
    }

    sqs_client = SQSClient(
        config=Config(region_name="eu-west-2"), queue_url=temp_queue.url
    )
    with temp_config(conf):
        config = ScrapeConfig()
        client_factory = ClientFactory(config.sts_region)

        executor = Executor(config, client_factory, sqs_client)
        results = await executor.discover_metrics(init_clients=True)
        assert results
        regional = results[("eu-west-2", None)]
        if expected == 0:
            assert not regional
        else:
            assert len(regional.keys()) == 1
            assert len(regional[(86400, 0, 60)]) == expected


async def test_s3_metric_discovery(test_bucket):

    conf = {
        "discovery": {
            "jobs": [
                {
                    "type": "s3",
                    "regions": ["eu-west-2"],
                    "metrics": [
                        {
                            "name": "NumberOfObjects",
                            "stats": ["Average"],
                            "period": 86400,
                        },
                        {
                            "name": "BucketSizeBytes",
                            "stats": ["Average"],
                            "period": 86400,
                        },
                    ],
                }
            ]
        }
    }

    with temp_config(conf):
        config = ScrapeConfig()
        client_factory = ClientFactory(config.sts_region)
        executor = Executor(config, client_factory, None)  # type: ignore[arg-type]
        discovered = await executor.discover_metrics(init_clients=True)
        assert discovered
        assert len(discovered) == 1
        region_result = discovered.get(("eu-west-2", None), {})
        assert region_result
        assert len(region_result) == 1
        metrics = region_result.get((86400, 0, 60))
        assert metrics
        assert len(metrics) == 2


async def test_alb_metric_discovery(test_bucket, temp_alb):

    alb_id, _alb_name = temp_alb
    conf = {
        "discovery": {
            "jobs": [
                {
                    "type": "alb",
                    "regions": ["eu-west-2"],
                    "metrics": [{"name": "RequestCount", "stats": ["Sum"]}],
                }
            ]
        }
    }

    with temp_config(conf):
        config = ScrapeConfig(
            rtf_overrides={"AWS/ApplicationELB": ["elasticloadbalancing:loadbalancer"]}
        )
        client_factory = ClientFactory(config.sts_region)
        executor = Executor(config, client_factory, None)  # type: ignore[arg-type]

        with temp_metrics(
            [
                MetricDatum(
                    namespace="AWS/ApplicationELB",
                    name="RequestCount",
                    value=10,
                    dimensions=[
                        {"Name": "LoadBalancer", "Value": alb_id},
                    ],
                    timestamp=datetime.now(tz=UTC).replace(second=0, microsecond=0),
                    unit="Count",
                )
            ]
        ):
            discovered = await executor.discover_metrics(init_clients=True)
        assert discovered
        assert len(discovered) == 1
        region_result = discovered.get(("eu-west-2", None), {})
        assert region_result
        assert len(region_result) == 1
        metrics = region_result.get((60, 0, 60))
        assert metrics
        assert len(metrics) == 1
