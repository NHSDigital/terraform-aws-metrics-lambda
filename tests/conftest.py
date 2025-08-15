import json
import os
import random
import re
import sys
from collections.abc import Generator
from typing import cast
from uuid import uuid4

import boto3
import pytest
from moto import mock_aws

sys.path.insert(0, f"{os.path.dirname(__file__)}/../src")


@pytest.fixture(scope="session", autouse=True)
def global_setup():
    os.environ.setdefault("LOCAL_MODE", "True")
    os.environ.setdefault("account", "local")
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

    with mock_aws():
        yield


@pytest.fixture
def s3():

    return boto3.resource("s3", region_name="eu-west-2")


@pytest.fixture
def test_bucket(s3):

    bucket_name = f"temp-{uuid4().hex}"
    bucket = s3.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
    )
    tagging = bucket.Tagging()
    tagging.put(Tagging={"TagSet": [{"Key": "project", "Value": "odin"}]})
    yield bucket

    bucket.objects.all().delete()
    bucket.delete()


@pytest.fixture
def sqs():

    return boto3.resource("sqs", region_name="eu-west-2")


@pytest.fixture
def temp_queue(sqs):

    queue_name = f"test-queue-{uuid4().hex}"
    queue = sqs.create_queue(
        QueueName=queue_name, Attributes={"VisibilityTimeout": "2"}
    )
    os.environ["QUEUE_NAME"] = queue_name
    yield queue
    os.environ.pop("QUEUE_NAME", None)
    queue.delete()


@pytest.fixture(scope="session")
def ec2():

    return boto3.client("ec2", region_name="eu-west-2")


@pytest.fixture(scope="session")
def vpc_id(ec2) -> str:

    response = ec2.create_vpc(
        CidrBlock="172.16.0.0/16",
    )
    return cast(str, response["Vpc"]["VpcId"])


@pytest.fixture
def subnet_id(ec2, vpc_id: str) -> Generator[str, None, None]:
    net = random.randint(1, 255)
    response = ec2.create_subnet(
        CidrBlock=f"172.16.{net}.0/24",
        VpcId=vpc_id,
    )
    yield response["Subnet"]["SubnetId"]

    ec2.delete_subnet(SubnetId=response["Subnet"]["SubnetId"])


@pytest.fixture
def temp_alb(subnet_id: str) -> Generator[tuple[str, str], None, None]:

    elb = boto3.client("elbv2", region_name="eu-west-2")
    alb_name = f"test-alb-{uuid4().hex}"
    _response = elb.create_load_balancer(
        Name=alb_name,
        Subnets=[
            subnet_id,
        ],
        Scheme="internal",
        Type="application",
        Tags=[{"Key": "Name", "Value": alb_name}],
    )
    arn = _response["LoadBalancers"][0]["LoadBalancerArn"]
    lb_id = re.sub(r"^arn:aws:elasticloadbalancing:.*?:loadbalancer/(.*)$", r"\1", arn)
    yield lb_id, alb_name
    elb.delete_load_balancer(
        LoadBalancerArn=_response["LoadBalancers"][0]["LoadBalancerArn"]
    )


@pytest.fixture
def temp_config(config: dict):
    os.environ["SCRAPE_CONFIG"] = json.dumps(config)
    yield
    os.environ.pop("SCRAPE_CONFIG", None)
