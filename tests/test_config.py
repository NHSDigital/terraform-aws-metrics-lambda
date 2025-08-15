from common import temp_config
from config import ScrapeConfig


def test_load_discovery_jobs():

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
        jobs = ScrapeConfig()
        assert len(jobs.discovery_jobs) == len(conf["discovery"]["jobs"])
