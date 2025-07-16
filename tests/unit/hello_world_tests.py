import os

import httpx
import pytest
from pytest_httpserver import HTTPServer


def test_basic():
    assert True


def test_dotenv_loaded():
    port = os.environ.get("LOCALSTACK_PORT")
    assert port
    assert port.isdigit()


def test_that_uses_temp_directory(tmp_path: str, new_uuid: str, free_tcp_port: int):

    with open(f"{tmp_path}/{new_uuid}.txt", mode="w") as f:
        f.write(str(free_tcp_port))

    with open(f"{tmp_path}/{new_uuid}.txt") as f:
        read = f.read()

    assert read
    assert read.isdigit()
    assert read == str(free_tcp_port)


@pytest.mark.asyncio
async def test_something_async(httpx_mock):
    httpx_mock.add_response()

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")

        assert response.status_code == 200


@pytest.mark.asyncio
async def test_json_client(httpserver: HTTPServer):
    httpserver.expect_request("/foobar").respond_with_json({"foo": "bar"})
    async with httpx.AsyncClient() as client:
        response = await client.get(httpserver.url_for("/foobar"))
        assert response.json() == {"foo": "bar"}
