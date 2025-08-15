import pytest
from botocore.config import Config
from clients import TaggingClient
from common import temp_config
from config import ScrapeConfig


@pytest.mark.parametrize(
    ("search_tags", "expected"),
    [
        ({}, 1),
        ({"project": "odin"}, 1),
        ({"project": "^od.*"}, 1),
        ({"project": ".*in$"}, 1),
        ({"project": "odin|another"}, 1),
        ({"project": "another"}, 0),
    ],
)
async def test_s3_get_resource(test_bucket, search_tags: dict, expected: int):

    conf = {
        "discovery": {
            "jobs": [
                {
                    "type": "s3",
                    "regions": ["eu-west-2"],
                    "search_tags": search_tags,
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
        jobs = ScrapeConfig()
        client = TaggingClient(Config(region_name="eu-west-2"))
        resources = await client.get_all_resources(jobs.discovery_jobs[0])
        assert len(resources) == expected


async def test_alb_get_resource(temp_alb):
    expected = 1
    _alb_arn, _alb_name = temp_alb
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
        jobs = ScrapeConfig(
            rtf_overrides={"AWS/ApplicationELB": ["elasticloadbalancing:loadbalancer"]}
        )
        client = TaggingClient(Config(region_name="eu-west-2"))
        resources = await client.get_all_resources(jobs.discovery_jobs[0])
        assert len(resources) == expected
