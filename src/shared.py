from math import floor
from time import time

from aws_lambda_powertools import Logger


def get_start_end(period: int, length: int, delay: int) -> tuple[float, float]:

    now = time()
    if period > 0:
        now = floor(now / period) * period

    start = now - length - delay
    end = now - delay
    return start, end


logger = Logger()
