import asyncio
import json
import os
from abc import ABC, abstractmethod
from asyncio import Semaphore
from collections.abc import AsyncGenerator, Callable
from functools import partial
from math import ceil
from typing import Any, TypeVar, cast

import boto3
import botocore.credentials
import botocore.session
from botocore.config import Config
from botocore.exceptions import ClientError
from model import (
    CloudwatchMetric,
    CloudwatchMetricResult,
    CloudwatchMetricTask,
    DiscoveryJob,
    MetricRequest,
    Resource,
    StaticJob,
)
from shared import get_start_end


async def run_in_executor[T](func: Callable[..., T], *args, **kwargs) -> T:
    """
        async wrapper for sync code
    Args:
        func: the function to call
        *args: positional args to pass to fund
        **kwargs: kwargs to pass to func

    Returns:

    """
    loop = asyncio.get_running_loop()

    to_execute = partial(func, *args, **kwargs)
    result = cast(T, await loop.run_in_executor(None, to_execute))

    return result


class RegionRoleClient:

    def __init__(
        self,
        client_name: str,
        config: Config,
        session: boto3.Session = None,
        concurrency: int = 5,
        pagination_token_name: str = "PaginationToken",
    ):
        session = session or boto3
        self.client: boto3.client = session.client(client_name, config=config)
        self._sf: Semaphore = Semaphore(concurrency)
        self._pagination_token_name = pagination_token_name

    async def _paginate(
        self, paginator_name: str, pagination_token_name: str | None = None, **kwargs
    ) -> AsyncGenerator[dict, None]:

        pagination_token_name = pagination_token_name or self._pagination_token_name

        paginator = self.client.get_paginator(paginator_name)

        page_iterator = paginator.paginate(**kwargs).__iter__()

        def _get_next_page():
            try:
                return page_iterator.__next__()
            except StopIteration:
                return None

        async with self._sf:
            page = await run_in_executor(_get_next_page)

        while page:
            pagination_token = page.get(pagination_token_name, None)
            yield page
            if not pagination_token:
                break

            async with self._sf:
                page = await run_in_executor(_get_next_page)


class CloudWatchClient(RegionRoleClient):
    def __init__(self, config: Config, session: boto3.Session = None):
        super().__init__(
            "cloudwatch",
            config,
            session,
            int(os.environ.get("METRICS_API_CONCURRENCY", 5)),
        )

    async def list_metrics(
        self, metric_name: str, job: DiscoveryJob
    ) -> AsyncGenerator[list[CloudwatchMetric], None]:
        kwargs = {
            "Namespace": job.ns,
            "MetricName": metric_name,
            "IncludeLinkedAccounts": job.linked_accounts,
        }
        if job.recently_active_only:
            kwargs["RecentlyActive"] = "PT3H"

        async for page in self._paginate("list_metrics", "NextToken", **kwargs):
            metrics = page.get("Metrics", [])
            results: list[CloudwatchMetric] = [
                CloudwatchMetric(
                    ns=metric["Namespace"],
                    name=metric["MetricName"],
                    dimensions={
                        d["Name"]: d["Value"] for d in metric.get("Dimensions", [])
                    },
                )
                for metric in metrics
            ]

            yield results

    async def get_metric_data(
        self,
        period: int,
        start: float,
        end: float,
        metric_tasks: list[CloudwatchMetricTask],
    ) -> AsyncGenerator[list[CloudwatchMetricTask], None]:
        total_metrics = len(metric_tasks)
        batch_size = 300  # max is 500 but scale back
        if total_metrics > batch_size:
            num_batches = ceil(total_metrics / 300)
            batch_size = ceil(total_metrics / num_batches)

        remaining: list[CloudwatchMetricTask] = metric_tasks

        task_by_id: dict[str, CloudwatchMetricTask] = {}

        while remaining:
            batch: list[CloudwatchMetricTask] = remaining[:batch_size]
            remaining = remaining[batch_size:]

            queries: list[dict] = []
            kwargs = {"StartTime": start, "EndTime": end, "MetricDataQueries": queries}

            for ix, task in enumerate(batch):
                task_id = f"m{ix}"
                task_by_id[task_id] = task
                query = {
                    "Id": task_id,
                    "MetricStat": {
                        "Metric": {
                            "Namespace": task.ns,
                            "MetricName": task.metric_name,
                            "Dimensions": [
                                {"Name": k, "Value": v}
                                for k, v in task.dimensions.items()
                            ],
                        },
                        "Period": period,
                        "Stat": task.statistic,
                        # 'Unit': 'Seconds'|'Microseconds'|'Milliseconds'|'Bytes'|'Kilobytes'|'Megabytes'
                        # |'Gigabytes'|'Terabytes'|'Bits'|'Kilobits'|'Megabits'|'Gigabits'|'Terabits'
                        # |'Percent'|'Count'|'Bytes/Second'|'Kilobytes/Second'|'Megabytes/Second'
                        # |'Gigabytes/Second'|'Terabytes/Second'|'Bits/Second'
                        # |'Kilobits/Second'|'Megabits/Second'|'Gigabits/Second'|'Terabits/Second'|'Count/Second'|'None'
                    },
                    "ReturnData": True,
                }
                queries.append(query)

            batch_metrics = []
            async for page in self._paginate(
                "get_metric_data", "PaginationToken", **kwargs
            ):
                results = page.get("MetricDataResults", [])

                for result in results:
                    task = task_by_id[result["Id"]]
                    if task.result:
                        task.result.timestamps.extend(result.get("Timestamps", []))
                        task.result.values.extend(result.get("Values", []))
                        continue

                    task.result = CloudwatchMetricResult(
                        values=result.get("Values", []),
                        timestamps=result.get("Timestamps", []),
                        status_code=result.get("StatusCode", ""),
                        messages=result.get("Messages", []),
                    )
                    batch_metrics.append(task)

            yield batch_metrics

    async def get_metric_statistics(
        self, metric: MetricRequest, job: StaticJob
    ) -> list[CloudwatchMetricTask]:

        start, end = get_start_end(metric.period, metric.length, metric.delay)

        kwargs: dict = {
            "Namespace": job.ns,
            "MetricName": metric.name,
            "StartTime": start,
            "EndTime": end,
            "Dimensions": [{"Name": k, "Value": v} for k, v in job.dimensions.items()],
            "Period": metric.period,
        }

        results: dict[str, CloudwatchMetricTask] = {
            stat: CloudwatchMetricTask(
                ns=job.ns,
                metric_name=metric.name,
                resource_name="static",
                dimensions=job.dimensions,
                statistic=stat,
                nil_to_zero=metric.nil_to_zero,
                add_cw_timestamp=metric.add_cw_timestamp,
                unit=metric.unit,
                tags={},
                result=CloudwatchMetricResult(values=[], timestamps=[]),
            )
            for stat in metric.stats
        }

        response = await run_in_executor(self.client.get_metric_statistics, **kwargs)
        datapoints = response.get("Datapoints", [])
        for datapoint in datapoints:
            unit = datapoint.get("Unit")
            timestamp = datapoint.get("Timestamp")
            for stat in metric.stats:
                task = results[stat]
                assert task.result
                if unit and unit != task.unit:
                    task.unit = unit
                val = datapoint.get(stat)
                if val:
                    task.result.values.append(val)
                    task.result.timestamps.append(timestamp)
                    continue

                val = datapoint.get("ExtendedStatistics", {}).get(stat)
                if not val:
                    continue
                task.result.values.append(val)
                task.result.timestamps.append(timestamp)
        return list(results.values())


class STSClient(RegionRoleClient):
    def __init__(self, config: Config, session: boto3.Session = None):
        super().__init__(
            "sts", config, session, int(os.environ.get("STS_API_CONCURRENCY", 5))
        )

        self._account_id: str | None = None
        self._account_id_lock = asyncio.Lock()

    async def get_account_id(self) -> str:

        if self._account_id is not None:
            return self._account_id

        async with self._account_id_lock:

            if self._account_id is not None:
                return self._account_id

            async with self._sf:
                try:
                    response = await run_in_executor(self.client.get_caller_identity)
                    self._account_id = response.get("Account", "")
                except ClientError:
                    self._account_id = ""

        return self._account_id

    def get_session_sync(
        self, role_arn: str, session_name: str | None = None
    ) -> boto3.Session:
        session_name = session_name or "metrics"

        response = self.client.assume_role(
            RoleArn=role_arn, RoleSessionName=session_name
        )

        creds = response["Credentials"]

        boto_credentials = botocore.credentials.Credentials(
            access_key=creds.get("AccessKeyId"),
            secret_key=creds.get("SecretAccessKey"),
            token=creds.get("SessionToken"),
            method="sts-assume-role",
        )

        session = botocore.session.get_session()

        session._credentials = boto_credentials  # type: ignore[attr-defined]

        return boto3.Session(botocore_session=session)

    async def get_session(
        self, role_arn: str, session_name: str | None = None
    ) -> boto3.Session:

        async with self._sf:
            session = await run_in_executor(
                self.get_session_sync, role_arn, session_name
            )

        return session


class SupportAppClient(RegionRoleClient):
    def __init__(self, config: Config, session: boto3.Session = None):
        super().__init__("support-app", config, session, 1)
        self._account_alias: str | None = None
        self._account_alias_lock = asyncio.Lock()

    async def get_account_alias(self) -> str:

        if self._account_alias is not None:
            return self._account_alias

        async with self._account_alias_lock:

            if self._account_alias is not None:
                return self._account_alias

            try:
                response = await run_in_executor(self.client.get_account_alias)
                self._account_alias = response.get("accountAlias", "")
            except ClientError:
                self._account_alias = ""

        return self._account_alias


class SQSClient:

    def __init__(self, queue_url: str, config: Config, session: boto3.Session = None):
        session = session or boto3
        self.client = session.client("sqs", config=config)
        self.queue_url = queue_url

    async def send_messages(self, messages: list[dict]):

        remaining = [
            {"Id": str(ix), "MessageBody": json.dumps(message)}
            for ix, message in enumerate(messages)
        ]

        while remaining:
            batch = remaining[:10]
            remaining = remaining[10:]
            response = await run_in_executor(
                self.client.send_message_batch, QueueUrl=self.queue_url, Entries=batch
            )
            assert response
        return True


class ResourceDiscovery(ABC):

    @abstractmethod
    async def paginate_resources(
        self, job: DiscoveryJob
    ) -> AsyncGenerator[list[Resource], None]:
        yield []

    async def get_all_resources(self, job: DiscoveryJob) -> list[Resource]:
        resources: list[Resource] = []
        async for page in self.paginate_resources(job):
            resources.extend(page)
        return resources


class TaggingClient(RegionRoleClient):

    def __init__(self, config: Config, session: boto3.Session = None):
        super().__init__(
            "resourcegroupstaggingapi",
            config,
            session,
            int(os.environ.get("TAGGING_API_CONCURRENCY", 5)),
        )

    async def paginate_resources(
        self, job: DiscoveryJob
    ) -> AsyncGenerator[list[Resource], None]:
        kwargs: dict[str, Any] = {"ResourceTypeFilters": job.resource_type_filters}
        if job.search_tags:
            kwargs["TagFilters"] = []
            for tag in job.search_tags:
                kwargs["TagFilters"].append({"Key": tag})
        async for page in self._paginate("get_resources", **kwargs):
            response = page.get("ResourceTagMappingList", [])
            resources: list[Resource] = []
            for resource in response:
                tags = {t["Key"]: t["Value"] for t in resource.get("Tags", [])}

                if job.search_tags and not all(
                    v.match(tags.get(k, "")) for k, v in job.search_tags.items()
                ):
                    continue

                resources.append(
                    Resource(ns=job.ns, arn=resource["ResourceARN"], tags=tags)
                )

            yield resources

    async def get_all_resources(self, job: DiscoveryJob) -> list[Resource]:
        resources: list[Resource] = []
        async for page in self.paginate_resources(job):
            resources.extend(page)
        return resources


class APIGatewayV1Client(RegionRoleClient):

    def __init__(self, config: Config, session: boto3.Session = None):
        super().__init__(
            "apigateway",
            config,
            session,
            int(os.environ.get("APIGATEWAY_API_CONCURRENCY", 5)),
            pagination_token_name="NextToken",
        )

    async def get_apis(self) -> list[dict]:
        apis: list[dict] = []
        async for page in self._paginate("get_rest_apis"):
            apis.extend(page.get("items", []))
        return apis


class APIGatewayV2Client(RegionRoleClient):

    def __init__(self, config: Config, session: boto3.Session = None):
        super().__init__(
            "apigatewayv2",
            config,
            session,
            int(os.environ.get("APIGATEWAYV2_API_CONCURRENCY", 5)),
            pagination_token_name="NextToken",
        )

    async def get_apis(self) -> list[dict]:
        apis: list[dict] = []
        async for page in self._paginate("get_apis"):
            apis.extend(page.get("Items", []))
        return apis


class ResourceFilter(ABC):

    @abstractmethod
    async def discover_or_filter(
        self, resources_in: list[Resource], job: DiscoveryJob
    ) -> list[Resource]:
        return []


class APIGatewayFilter(ResourceFilter):

    def __init__(self, config: Config, session: boto3.Session = None):
        self.v1_client = APIGatewayV1Client(config, session)
        self.v2_client = APIGatewayV2Client(config, session)

    async def discover_or_filter(
        self, resources: list[Resource], job: DiscoveryJob
    ) -> list[Resource]:

        if not resources:
            return resources

        v1_apis = await self.v1_client.get_apis()
        v2_apis = await self.v2_client.get_apis()
        resources_out: list[Resource] = []
        for resource in resources:
            for item in v1_apis:
                if not resource.arn.endswith(f"/restapis/{item['id']}"):
                    continue

                resource.arn = resource.arn.replace(item["id"], item["name"])
                resources_out.append(resource)
                break

            for item in v2_apis:
                if not resource.arn.endswith(f"/apis/{item['ApiId']}"):
                    continue
                resources_out.append(resource)
                break

        return resources_out


class AutoScalingClient(RegionRoleClient, ResourceFilter):

    def __init__(self, config: Config, session: boto3.Session = None):
        super().__init__(
            "autoscaling",
            config,
            session,
            int(os.environ.get("AUTOSCALING_API_CONCURRENCY", 5)),
            pagination_token_name="NextToken",
        )

    async def discover_or_filter(
        self, _resources: list[Resource], job: DiscoveryJob
    ) -> list[Resource]:

        resources: list[Resource] = []

        async for page in self._paginate("describe_auto_scaling_groups"):
            items = page.get("AutoScalingGroups", [])
            for item in items:
                tags = {t["Key"]: t["Value"] for t in item.get("Tags", [])}
                if job.search_tags and not all(
                    v.match(tags.get(k, "")) for k, v in job.search_tags.items()
                ):
                    continue
                resources.append(
                    Resource(ns=job.ns, arn=item["AutoScalingGroupARN"], tags=tags)
                )

        return resources


class DMSClient(RegionRoleClient, ResourceFilter):

    def __init__(self, config: Config, session: boto3.Session = None):
        super().__init__(
            "dms",
            config,
            session,
            int(os.environ.get("DMS_API_CONCURRENCY", 5)),
            pagination_token_name="NextToken",
        )

    async def discover_or_filter(
        self, resources: list[Resource], job: DiscoveryJob
    ) -> list[Resource]:

        if not resources:
            return []

        repl_instance_ids = {}

        async for page in self._paginate(
            "describe_replication_instances", pagination_token_name="Marker"
        ):
            items = page.get("ReplicationInstances", [])
            for item in items:
                repl_instance_ids[item["ReplicationInstanceArn"]] = item[
                    "ReplicationInstanceIdentifier"
                ]

        async for page in self._paginate("describe_replication_tasks"):
            items = page.get("ReplicationTasks", [])
            for item in items:
                instance_id = repl_instance_ids[item["ReplicationInstanceArn"]]
                if not instance_id:
                    continue
                repl_instance_ids[item["ReplicationTaskArn"]] = instance_id

        for resource in resources:
            instance_id = repl_instance_ids.get(resource.arn)
            if not instance_id:
                continue
            resource.arn = f"{resource.arn}/{instance_id}"

        return resources


class EC2Client(RegionRoleClient, ResourceFilter):

    def __init__(self, config: Config, session: boto3.Session = None):
        super().__init__(
            "ec2",
            config,
            session,
            int(os.environ.get("EC2_API_CONCURRENCY", 5)),
            pagination_token_name="NextToken",
        )

    async def filter_ec2_spot_resources(
        self, _resources: list[Resource], job: DiscoveryJob
    ) -> list[Resource]:

        resources: list[Resource] = []

        async for page in self._paginate("describe_spot_fleet_requests"):
            items = page.get("SpotFleetRequestConfigs", [])
            for item in items:
                tags = {t["Key"]: t["Value"] for t in item.get("Tags", [])}
                if job.search_tags and not all(
                    v.match(tags.get(k, "")) for k, v in job.search_tags.items()
                ):
                    continue

                resources.append(
                    Resource(ns=job.ns, arn=item["SpotFleetRequestId"], tags=tags)
                )

        return resources

    async def filter_transit_gateway_resources(
        self, _resources: list[Resource], job: DiscoveryJob
    ) -> list[Resource]:

        resources: list[Resource] = []

        async for page in self._paginate("describe_transit_gateway_attachments"):
            items = page.get("TransitGatewayAttachments", [])
            for item in items:
                tags = {t["Key"]: t["Value"] for t in item.get("Tags", [])}
                if job.search_tags and not all(
                    v.match(tags.get(k, "")) for k, v in job.search_tags.items()
                ):
                    continue

                resources.append(
                    Resource(
                        ns=job.ns,
                        arn=f"{item["TransitGatewayId"]}/{item['TransitGatewayAttachmentId']}",
                        tags=tags,
                    )
                )

        return resources

    async def discover_or_filter(
        self, resources: list[Resource], job: DiscoveryJob
    ) -> list[Resource]:

        if job.ns == "AWS/EC2Spot":
            return await self.filter_ec2_spot_resources(resources, job)

        if job.ns == "AWS/TransitGateway":
            return await self.filter_transit_gateway_resources(resources, job)

        return resources


class PrometheusClient(RegionRoleClient, ResourceFilter):

    def __init__(self, config: Config, session: boto3.Session = None):
        super().__init__(
            "amp",
            config,
            session,
            int(os.environ.get("PROMETHEUS_API_CONCURRENCY", 5)),
            pagination_token_name="nextToken",
        )

    async def discover_or_filter(
        self, _resources: list[Resource], job: DiscoveryJob
    ) -> list[Resource]:

        resources: list[Resource] = []

        async for page in self._paginate("list_workspaces"):
            items = page.get("workspaces", [])
            for item in items:
                tags = item.get("tags", {})
                if job.search_tags and not all(
                    v.match(tags.get(k, "")) for k, v in job.search_tags.items()
                ):
                    continue

                resources.append(Resource(ns=job.ns, arn=item["arn"], tags=tags))

        return resources


class StorageGatewayClient(RegionRoleClient, ResourceFilter):

    def __init__(self, config: Config, session: boto3.Session = None):
        super().__init__(
            "storagegateway",
            config,
            session,
            int(os.environ.get("PROMETHEUS_API_CONCURRENCY", 5)),
            pagination_token_name="Marker",
        )

    async def discover_or_filter(
        self, _resources: list[Resource], job: DiscoveryJob
    ) -> list[Resource]:

        resources: list[Resource] = []

        async for page in self._paginate("list_gateways"):
            items = page.get("Gateways", [])
            for item in items:

                tags_resp = await self.client.list_tags_for_resource(
                    ResourceARN=item["GatewayARN"]
                )
                tags = {tag["Key"]: tag["Value"] for tag in tags_resp.get("Tags", [])}
                if job.search_tags and not all(
                    v.match(tags.get(k, "")) for k, v in job.search_tags.items()
                ):
                    continue

                resources.append(
                    Resource(
                        ns=job.ns,
                        arn=f"{item['GatewayId']}/{item['GatewayName']}",
                        tags=tags,
                    )
                )

        return resources


class ShieldClient(RegionRoleClient, ResourceFilter):

    def __init__(self, config: Config, session: boto3.Session = None):
        super().__init__(
            "shield",
            config,
            session,
            int(os.environ.get("SHIELD_API_CONCURRENCY", 5)),
            pagination_token_name="NextToken",
        )

    async def discover_or_filter(
        self, _resources: list[Resource], job: DiscoveryJob
    ) -> list[Resource]:

        resources: list[Resource] = []

        async for page in self._paginate("list_protections"):
            items = page.get("Protections", [])
            resources.extend(
                Resource(
                    ns=job.ns,
                    arn=item["ResourceArn"],
                    tags={"ProtectionArn": item["ProtectionArn"]},
                )
                for item in items
            )

        return resources


TClientType = TypeVar("TClientType", bound=RegionRoleClient)

DISCOVERY_FILTERS = {
    "AWS/ApiGateway": APIGatewayFilter,
    "AWS/AutoScaling": AutoScalingClient,
    "AWS/DMS": DMSClient,
    "AWS/EC2Spot": EC2Client,
    "AWS/Prometheus": PrometheusClient,
    "AWS/StorageGateway": StorageGatewayClient,
    "AWS/TransitGateway": EC2Client,
    "AWS/DDoSProtection": ShieldClient,
}


class ClientFactory:
    def __init__(
        self, sts_region: str = "eu-west-2", base_config_args: dict | None = None
    ):
        self._base_session = boto3.Session()
        self._sts_region = sts_region
        base_config_args = base_config_args or {"region_name": "eu-west-2"}
        self._base_config = Config(**base_config_args)
        self._region_config = {base_config_args["region_name"]: self._base_config}
        if sts_region not in self._region_config:
            self._region_config[sts_region] = self._base_config.merge(
                Config(region_name=sts_region)
            )

        self._sts = STSClient(config=self._region_config[sts_region])
        self._sessions: dict[str, boto3.Session] = {}
        self._clients: dict[tuple[type, str, str | None], RegionRoleClient] = {
            (STSClient, sts_region, None): self._sts
        }
        # self._sts_clients: dict[tuple[str, str | None], STSClient] = {
        #     (sts_region, None): self._sts
        # }
        # self._support_clients: dict[str | None, SupportAppClient] = {}
        # self._tagging_clients: dict[tuple[str, str | None], TaggingClient] = {}
        # self._cloudwatch_clients: dict[tuple[str, str | None], CloudWatchClient] = {}
        self._session_lock = asyncio.Lock()

    def region_config(self, region: str) -> Config:
        config = self._region_config.get(region)
        if not config:
            config = self._base_config.merge(Config(region_name=region))
            self._region_config[region] = config
        return config

    def get_sqs_client(
        self, queue_url: str, region: str, role: str | None = None
    ) -> SQSClient:
        if not role:
            return SQSClient(
                queue_url=queue_url,
                config=self.region_config(region),
                session=self._base_session,
            )
        session = self._sts.get_session_sync(role)
        self._sessions[role] = session
        return SQSClient(
            queue_url=queue_url, config=self.region_config(region), session=session
        )

    @staticmethod
    def discovery_required_clients(jobs: list[DiscoveryJob]) -> set[type]:
        required: set[type] = set()
        tagging_added = False
        for job in jobs:
            if job.resource_type_filters and not tagging_added:
                required.add(TaggingClient)
                tagging_added = True

            discovery_filter = DISCOVERY_FILTERS.get(job.ns)
            if not discovery_filter:
                continue
            required.add(discovery_filter)

        return required

    async def get_session(self, role: str | None = None) -> boto3.Session:

        if not role:
            return self._base_session

        session = self._sessions.get(role)
        if session:
            return session

        async with self._session_lock:
            if role not in self._sessions:
                self._sessions[role] = await self._sts.get_session(role)
            return self._sessions[role]

    async def get_client(
        self, client_type: type[TClientType], region: str, role: str | None = None
    ) -> TClientType:

        if client_type is SupportAppClient:
            return cast(
                TClientType,
                await self._get_client(cast(type, client_type), "us-east-1", role),
            )

        return cast(
            TClientType, await self._get_client(cast(type, client_type), region, role)
        )

    async def _get_client(
        self, client_type: type, region: str, role: str | None = None
    ) -> RegionRoleClient:

        key = (client_type, region, role)
        client = self._clients.get(key)
        if client:
            return client
        session = (await self.get_session(role)) if role else self._base_session
        client = self._clients.get(key)
        if client:
            return client

        client = client_type(config=self.region_config(region), session=session)
        self._clients[key] = cast(RegionRoleClient, client)

        return cast(SupportAppClient, client)
