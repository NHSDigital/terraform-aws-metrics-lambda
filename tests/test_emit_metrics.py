import json
from datetime import UTC, datetime
from uuid import uuid4

import boto3
from botocore.config import Config
from clients import ClientFactory, SQSClient
from common import temp_config, temp_metrics
from config import ScrapeConfig
from dateutil.relativedelta import relativedelta
from executor import Executor
from moto.cloudwatch.models import MetricDatum


def _read_all_messages(queue_url) -> list[dict]:
    messages = []
    sqs = boto3.client("sqs", region_name="eu-west-2")
    while True:
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=10,
        )
        messages.extend([json.loads(m["Body"]) for m in response.get("Messages", [])])
        if not response.get("Messages"):
            break
    return messages


def _get_sqs_client(queue_url: str) -> SQSClient:
    return SQSClient(queue_url=queue_url, config=Config(region_name="eu-west-2"))


async def test_s3_discovery_scrape_and_emit(test_bucket, temp_queue):

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
                            "period": 60,
                            "length": 86400,  # moto incorrectly excludes 00:00:00 metrics for s3
                        },
                        {
                            "name": "BucketSizeBytes",
                            "stats": ["Average"],
                            "period": 60,
                            "length": 86400,  # moto incorrectly excludes 00:00:00 metrics for s3
                        },
                    ],
                }
            ]
        }
    }
    new_object = test_bucket.Object(f"test-{uuid4().hex}")
    new_object.put(Body=b"test")

    # cloudwatch = boto3.client("cloudwatch", region_name="eu-west-2")
    sqs_client = _get_sqs_client(temp_queue.url)
    with temp_config(conf):
        config = ScrapeConfig()
        client_factory = ClientFactory(config.sts_region)

        executor = Executor(config, client_factory, sqs_client)
        results = await executor.scrape_and_emit()
        assert results
        region_results = results[("eu-west-2", None)]
        assert region_results
        metrics = _read_all_messages(temp_queue.url)
        assert len(metrics) == 2
        for metric in metrics:
            assert metric["metric_name"] in (
                "NumberOfObjects",
                "BucketSizeBytes",
            )


async def test_alb_discovery_scrape_and_emit(temp_queue, temp_alb):
    alb_id, _alb_name = temp_alb

    conf = {
        "discovery": {
            "jobs": [
                {
                    "type": "alb",
                    "regions": ["eu-west-2"],
                    "metrics": [
                        {
                            "name": "RequestCount",
                            "stats": ["Sum", "SampleCount", "Maximum"],
                        }
                    ],
                }
            ]
        }
    }

    sqs_client = _get_sqs_client(temp_queue.url)
    with temp_config(conf):
        config = ScrapeConfig(
            rtf_overrides={"AWS/ApplicationELB": ["elasticloadbalancing:loadbalancer"]}
        )
        client_factory = ClientFactory(config.sts_region)

        executor = Executor(config, client_factory, sqs_client)
        with temp_metrics(
            [
                MetricDatum(
                    namespace="AWS/ApplicationELB",
                    name="RequestCount",
                    value=10,
                    dimensions=[
                        {"Name": "LoadBalancer", "Value": alb_id},
                    ],
                    timestamp=datetime.now(tz=UTC).replace(second=0, microsecond=0)
                    - relativedelta(minutes=1),
                    unit="Count",
                )
            ]
        ):

            results = await executor.scrape_and_emit()
        assert results
        region_results = results[("eu-west-2", None)]
        assert region_results
        messages = _read_all_messages(temp_queue.url)
        assert len(messages) == 1
        assert messages[0]["metric_name"] == "RequestCount"
        assert messages[0]["value"]["sum"] == 10.0
        assert messages[0]["value"]["count"] == 1
        assert messages[0]["value"]["max"] == 10
