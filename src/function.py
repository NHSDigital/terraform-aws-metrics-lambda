import asyncio
import os

from aws_lambda_powertools.utilities.typing import LambdaContext
from clients import ClientFactory
from config import ScrapeConfig
from executor import Executor
from shared import logger

config: ScrapeConfig | None = None


def _ensure_config():
    global config
    if config:
        return
    try:
        config = ScrapeConfig()
    except Exception as e:
        logger.exception("failed to load config")
        raise e


@logger.inject_lambda_context(log_event=False)
def handler(_event: dict, _context: LambdaContext):

    global config

    if not config:
        try:
            config = ScrapeConfig()
        except Exception as e:
            logger.exception("failed to load config")
            raise e

    loop = asyncio.get_event_loop()
    client_factory = ClientFactory(
        config.sts_region, base_config_args=config.boto_kwargs
    )
    queue_url = os.environ["QUEUE_URL"]
    queue_region = os.environ.get("QUEUE_REGION", config.default_region)
    queue_role = os.environ.get("QUEUE_ROLE") or None
    # init this sync, if we can't do this there's no point continuing
    sqs_client = client_factory.get_sqs_client(queue_url, queue_region, queue_role)
    executor = Executor(config, client_factory, sqs_client)
    _result = loop.run_until_complete(executor.scrape_and_emit())


# if __name__ == "__main__":
#     handler(None, None)
