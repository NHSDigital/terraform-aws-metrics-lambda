import asyncio
import itertools
import re
from collections import defaultdict
from typing import Any, cast

from associator import Associator, NoOpAssociator
from clients import (
    DISCOVERY_FILTERS,
    ClientFactory,
    CloudWatchClient,
    ResourceFilter,
    SQSClient,
    STSClient,
    SupportAppClient,
    TaggingClient,
)
from config import ScrapeConfig
from model import (
    CloudwatchMetricTask,
    DiscoveryJob,
    MetricStats,
    MetricTaskSignature,
    Resource,
    StaticJob,
)
from shared import get_start_end, logger


class Executor:

    def __init__(
        self, config: ScrapeConfig, client_factory: ClientFactory, sqs_client: SQSClient
    ):
        self.config = config
        self.client_factory = client_factory
        self.sqs_client = sqs_client
        self.executors = self._get_executors()

    def _get_executors(self):

        discovery_jobs: dict[tuple[str, str | None], list[DiscoveryJob]] = defaultdict(
            list
        )

        if self.config.discovery_jobs:
            for region, role, discovery_job in itertools.chain(
                *(
                    discovery_job.sub_jobs(self.config.default_region)
                    for discovery_job in self.config.discovery_jobs
                )
            ):
                discovery_jobs[(region, role)].append(discovery_job)

        static_jobs: dict[tuple[str, str | None], list[StaticJob]] = defaultdict(list)
        if self.config.static_jobs:
            for region, role, static_job in itertools.chain(
                *(
                    static_job.sub_jobs(self.config.default_region)
                    for static_job in self.config.static_jobs
                )
            ):
                static_jobs[(region, role)].append(static_job)

        region_roles = set(itertools.chain(discovery_jobs.keys(), static_jobs.keys()))

        return [
            RegionRoleExecutor(
                region=rr[0],
                role=rr[1],
                config=self.config,
                discovery_jobs=discovery_jobs[rr],
                static_jobs=static_jobs[rr],
                sqs_client=self.sqs_client,
                client_factory=self.client_factory,
            )
            for rr in region_roles
        ]

    async def scrape_and_emit(self) -> dict[tuple[str, str | None], list[MetricStats]]:

        async def _scrape(
            ex: RegionRoleExecutor,
        ) -> tuple[tuple[str, str | None], list[MetricStats]]:
            metrics = await ex.scrape_and_emit()
            return (ex.region, ex.role), metrics

        tasks = [_scrape(ex) for ex in self.executors]

        results = await asyncio.gather(*tasks)

        return dict(results)

    async def discover_metrics(
        self, init_clients: bool = False
    ) -> dict[
        tuple[str, str | None], dict[tuple[int, int, int], list[CloudwatchMetricTask]]
    ]:

        async def _executor_result(
            ex: RegionRoleExecutor,
        ) -> tuple[
            str, str | None, dict[tuple[int, int, int], list[CloudwatchMetricTask]]
        ]:
            shards = await ex.discover_metrics(init_clients=init_clients)
            metrics = cast(
                dict[tuple[int, int, int], list[CloudwatchMetricTask]],
                defaultdict(list),
            )
            for shard in shards:
                for (period, delay, length), tasks in shard.items():
                    metrics[(period, delay, length)].extend(tasks)

            return ex.region, ex.role, metrics

        exec_tasks = [_executor_result(ex) for ex in self.executors]

        results = await asyncio.gather(*exec_tasks)

        return {(region, role): metrics for region, role, metrics in results}


class RegionRoleExecutor:

    def __init__(
        self,
        region: str,
        role: str | None,
        config: ScrapeConfig,
        discovery_jobs: list[DiscoveryJob],
        static_jobs: list[StaticJob],
        sqs_client: SQSClient,
        client_factory: ClientFactory,
    ):
        self.config = config
        self.sqs = sqs_client
        self.client_factory = client_factory
        self.region = region
        self.role = role
        self.discovery_jobs = discovery_jobs or []
        self.static_jobs = static_jobs or []
        self._clients: dict[type, Any] = {}

    @property
    def cloudwatch(self) -> CloudWatchClient:
        client = self._clients.get(CloudWatchClient)
        if not client:
            raise ValueError("await ensure_clients() first")
        return cast(CloudWatchClient, client)

    @property
    def tagging(self) -> TaggingClient:
        client = self._clients.get(TaggingClient)
        if not client:
            raise ValueError("await ensure_clients() first")
        return cast(TaggingClient, client)

    @property
    def sts(self) -> STSClient:
        client = self._clients.get(STSClient)
        if not client:
            raise ValueError("await ensure_clients() first")
        return cast(STSClient, client)

    @property
    def support(self) -> SupportAppClient:
        client = self._clients.get(SupportAppClient)
        if not client:
            raise ValueError("await ensure_clients() first")
        return cast(SupportAppClient, client)

    async def ensure_clients(self, *types):
        for client_type in types:
            if client_type in self._clients:
                continue
            self._clients[client_type] = await self.client_factory.get_client(
                client_type, self.region, self.role
            )

    async def scrape_and_emit(self) -> list[MetricStats]:
        logger.info(f"scraping  {self.region} {self.role}")

        try:
            await self.ensure_clients(
                STSClient,
                SupportAppClient,
                CloudWatchClient,
                *self.client_factory.discovery_required_clients(self.discovery_jobs),
            )

            account_id = await self.sts.get_account_id()
            account_alias = await self.support.get_account_alias()

            labels = {"region": self.region}

            if account_id:
                labels["account_id"] = account_id

            if account_alias:
                labels["account_alias"] = account_alias

            stats: dict[tuple[str, str], MetricStats] = {}

            results: list[list[MetricStats]] = []

            discovered_metrics = await self.get_batched_discovery_metrics()
            if discovered_metrics:
                discovery_tasks = [
                    self.get_discovered_batch_and_emit(
                        period, delay, length, tasks, context_labels=labels
                    )
                    for (period, delay), (length, tasks) in discovered_metrics.items()
                ]
                discovery_results = await asyncio.gather(*discovery_tasks)

                results.extend(discovery_results)

            if self.static_jobs:
                static_results = await self.get_static_metrics_emit(
                    context_labels=labels, static_jobs=self.static_jobs
                )
                results.extend([static_results])

            for stat in cast(list[MetricStats], itertools.chain(*results)):
                key = (stat.ns, stat.name)
                existing = stats.get(key)
                if not existing:
                    stats[key] = stat
                    continue

                existing.count += stat.count

            return list(stats.values())
        except Exception as e:
            logger.exception(f"scraping {self.region} {self.role} failed")
            raise e

    @staticmethod
    def _group_metrics_to_message(
        context_labels: dict[str, str], metric_tasks: list[CloudwatchMetricTask]
    ) -> dict:

        message: dict = dict(context_labels.items())
        values: dict[str, float | int | None] = {}
        message["value"] = values
        for task in metric_tasks:
            message["namespace"] = task.ns
            message["metric_name"] = task.metric_name
            message["tags"] = task.tags
            message["dimensions"] = task.dimensions

            stat = task.stat_shortname()
            if stat in values:
                raise ValueError(f"duplicate stat {stat} in metric tasks")

            values[stat] = task.get_value()

            ts = task.get_timestamp()
            if not ts:
                continue

            existing = message.get("timestamp") or 0
            if ts <= existing:
                continue
            # use the most recent timestamp
            message["timestamp"] = ts

        return message

    async def get_static_metrics_emit(
        self,
        context_labels: dict[str, str],
        static_jobs: list[StaticJob],
    ) -> list[MetricStats]:

        tasks = [
            self.cloudwatch.get_metric_statistics(metric, job)
            for job in static_jobs
            for metric in job.metrics
        ]

        results = await asyncio.gather(*tasks)

        stats: dict[tuple[str, str], int] = defaultdict(int)

        for stat in itertools.chain(*results):
            stats[(stat.ns, stat.metric_name)] += 1

        messages = [
            self._group_metrics_to_message(context_labels, tasks) for tasks in results
        ]
        if messages:
            await self.sqs.send_messages(messages)

        return [
            MetricStats(ns=ns, name=name, count=count)
            for (ns, name), count in stats.items()
        ]

    async def get_discovered_batch_and_emit(
        self,
        period: int,
        delay: int,
        length: int,
        metric_tasks: list[CloudwatchMetricTask],
        context_labels: dict[str, str],
    ) -> list[MetricStats]:

        start, end = get_start_end(period, length, delay)

        stats: dict[tuple[str, str], int] = defaultdict(int)

        grouped_by_metric: dict[MetricTaskSignature, list[CloudwatchMetricTask]] = (
            defaultdict(list)
        )

        async for page in self.cloudwatch.get_metric_data(
            period, start, end, metric_tasks
        ):

            for task in page:
                if not task.result or not task.result.values:
                    continue

                grouped_by_metric[task.signature].append(task)
                stats[(task.ns, task.metric_name)] += 1

        messages = [
            self._group_metrics_to_message(context_labels, tasks)
            for tasks in grouped_by_metric.values()
        ]
        if messages:
            await self.sqs.send_messages(messages)

        return [
            MetricStats(ns=ns, name=name, count=count)
            for (ns, name), count in stats.items()
        ]

    async def get_batched_discovery_metrics(
        self, init_clients: bool = False
    ) -> dict[tuple[int, int], tuple[int, list[CloudwatchMetricTask]]]:

        period_delay_batched_metrics: dict[
            tuple[int, int], tuple[int, list[CloudwatchMetricTask]]
        ] = {}

        if self.discovery_jobs:

            discovery_batches = await self.discover_metrics(init_clients=init_clients)
            for batch in discovery_batches:
                for (period, delay, length), tasks in batch.items():
                    existing = period_delay_batched_metrics.get((period, delay))
                    if not existing:
                        period_delay_batched_metrics[(period, delay)] = (length, tasks)
                        continue

                    existing[1].extend(tasks)
                    if existing[0] < length:
                        # track the longest length for the period/delay
                        period_delay_batched_metrics[(period, delay)] = (
                            length,
                            existing[1],
                        )

        return period_delay_batched_metrics

    async def discover_metrics(
        self, init_clients: bool = False
    ) -> list[dict[tuple[int, int, int], list[CloudwatchMetricTask]]]:

        if not self.discovery_jobs:
            return []

        if init_clients:
            await self.ensure_clients(
                CloudWatchClient,
                *self.client_factory.discovery_required_clients(self.discovery_jobs),
            )

        discovery_tasks = [self.run_discovery_job(job) for job in self.discovery_jobs]

        discovery_results = await asyncio.gather(*discovery_tasks)

        return discovery_results

    async def run_discovery_job(  # noqa: C901
        self, job: DiscoveryJob
    ) -> dict[tuple[int, int, int], list[CloudwatchMetricTask]]:

        resources: list[Resource] = []
        if job.resource_type_filters:
            resources = await self.tagging.get_all_resources(job)

        resource_filter_type = DISCOVERY_FILTERS.get(job.ns)
        if resource_filter_type:
            resource_filter = cast(
                ResourceFilter,
                await self.client_factory.get_client(
                    resource_filter_type, self.region, self.role
                ),
            )
            resources = await resource_filter.discover_or_filter(resources, job)

        associator = (
            Associator(job.dimensions_regexps, resources)
            if resources and job.dimensions_regexps
            else NoOpAssociator()
        )

        metrics_requests: dict[tuple[int, int, int], list[CloudwatchMetricTask]] = (
            defaultdict(list)
        )
        for metric_req in job.metrics:
            async for page in self.cloudwatch.list_metrics(metric_req.name, job):
                for metric in page:

                    exact_dimensions = job.dimensions_exact
                    # shallow clone
                    search_dimensions: dict[str, re.Pattern] = dict(
                        (job.search_dimensions or {}).items()
                    )

                    if metric_req.dimensions_exact is not None:
                        exact_dimensions = metric_req.dimensions_exact

                    if metric_req.search_dimensions:
                        if metric_req.merge_dimensions:
                            search_dimensions.update(metric_req.search_dimensions)
                        else:
                            search_dimensions = metric_req.search_dimensions

                    if (
                        exact_dimensions
                        and set(search_dimensions.keys()) != metric.dimension_names
                    ):
                        continue

                    if search_dimensions and not all(
                        v.match(metric.dimensions.get(k, ""))
                        for k, v in search_dimensions.items()
                    ):
                        continue

                    resource, skip = associator.associate_metric_to_resource(metric)
                    if skip:
                        continue

                    resource = resource or Resource(ns=job.ns, arn="global", tags={})

                    tags = (
                        {k: resource.tags.get(k, "") for k in job.exported_tags}
                        if job.exported_tags
                        else {}
                    )

                    tags.update(job.custom_tags)

                    for stat in metric_req.stats:
                        metrics_requests[
                            (metric_req.period, metric_req.delay, metric_req.length)
                        ].append(
                            CloudwatchMetricTask(
                                ns=job.ns,
                                metric_name=metric_req.name,
                                resource_name=resource.arn,
                                dimensions=metric.dimensions,
                                statistic=stat,
                                nil_to_zero=metric_req.nil_to_zero,
                                add_cw_timestamp=metric_req.add_cw_timestamp,
                                unit=metric_req.unit,
                                tags=tags,
                            )
                        )

        return metrics_requests

    async def namespace_specific_resource_discovery(
        self, job: DiscoveryJob
    ) -> list[Resource] | None:
        return []
