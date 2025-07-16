import os
import socket
from contextlib import closing
from uuid import uuid4

import pytest
from dotenv import load_dotenv

from . import PROJECT_ROOT

load_dotenv(f"{PROJECT_ROOT}/.env")

# check pytest built in fixtures: https://docs.pytest.org/en/stable/builtin.html


@pytest.fixture(scope="session", autouse=True)
def global_setup():
    os.environ.setdefault("LOCAL_MODE", "True")
    os.environ.setdefault("account", "local")
    os.environ.setdefault(
        "LOCALSTACK_ENDPOINT", f"http://localhost:{os.environ['LOCALSTACK_PORT']}"
    )


@pytest.fixture
def new_uuid():
    return uuid4().hex


@pytest.fixture
def unallocated_tcp_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def session_singleton_example():

    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)):
        # possibly expensive setup steps
        yield socket
        # steps to tear down after creating fixture
        test = None
        print(test)
