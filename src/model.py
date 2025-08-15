import itertools
import re
from collections.abc import Generator
from dataclasses import dataclass, field
from datetime import datetime
from typing import cast


@dataclass
class Service:
    aka: str
    ns: str
    rtf: list[str] = field(default_factory=list)
    rex: list[re.Pattern[str]] = field(default_factory=list)

    def __post_init__(self):
        self.rex = [re.compile(r) for r in (self.rex or [])]


@dataclass
class MetricRequest:
    name: str
    stats: list[str]
    period: int = 60
    length: int = 60
    delay: int = 0
    nil_to_zero: bool = False
    add_cw_timestamp: bool = True
    unit: str | None = None

    search_dimensions: dict[str, re.Pattern[str]] = field(default_factory=dict)
    merge_dimensions: bool = True
    dimensions_exact: bool | None = None

    def __post_init__(self):
        self.search_dimensions = {
            k: re.compile(v) for k, v in (self.search_dimensions or {}).items()
        }


@dataclass
class DiscoveryJob:
    ns: str
    metrics: list[MetricRequest]
    regions: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)

    custom_tags: dict[str, str] = field(default_factory=dict)

    search_tags: dict[str, re.Pattern[str]] = field(default_factory=dict)
    search_dimensions: dict[str, re.Pattern[str]] = field(default_factory=dict)
    dimensions_exact: bool = False

    recently_active_only: bool = True
    linked_accounts: bool = False
    # from service
    dimensions_regexps: list[re.Pattern[str]] = field(default_factory=list)
    resource_type_filters: list[str] = field(default_factory=list)
    # from config
    exported_tags: set[str] = field(default_factory=set)

    def __post_init__(self):
        self.regions = [r for r in (self.regions or []) if r]
        self.roles = [r for r in (self.roles or []) if r]
        self.search_tags = {
            k: re.compile(v) for k, v in (self.search_tags or {}).items()
        }
        self.search_dimensions = {
            k: re.compile(v) for k, v in (self.search_dimensions or {}).items()
        }

    def sub_jobs(
        self, default_region: str
    ) -> Generator[tuple[str, str | None, "DiscoveryJob"], None, None]:
        regions = self.regions or [default_region]
        roles = self.roles or [None]  # type: ignore[list-item]

        return cast(
            Generator[tuple[str, str | None, DiscoveryJob], None, None],
            itertools.product(regions, roles, [self]),
        )


@dataclass
class StaticJob:
    ns: str
    metrics: list[MetricRequest]
    regions: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    custom_tags: dict[str, str] = field(default_factory=dict)
    dimensions: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        self.regions = [r for r in (self.regions or []) if r]
        self.roles = [r for r in (self.roles or []) if r]

    def sub_jobs(
        self, default_region: str
    ) -> Generator[tuple[str, str | None, "StaticJob"], None, None]:
        regions = self.regions or [default_region]
        roles = self.roles or [None]  # type: ignore[list-item]

        return cast(
            Generator[tuple[str, str | None, StaticJob], None, None],
            itertools.product(regions, roles, [self]),
        )


@dataclass
class Resource:
    ns: str
    arn: str
    tags: dict[str, str]
    mapped: bool = False


@dataclass
class CloudwatchMetric:
    ns: str
    name: str
    dimensions: dict[str, str]
    dimension_names: set[str] = None  # type: ignore[assignment]

    def __post_init__(self):
        self.dimension_names = set(self.dimensions.keys())


@dataclass
class CloudwatchMetricResult:
    timestamps: list[datetime]
    values: list[float]
    status_code: str | None = None
    messages: list[dict[str, str]] | None = None


type MetricTaskSignature = tuple[
    str, str, tuple[tuple[str, str], ...], tuple[tuple[str, str], ...]
]


@dataclass
class CloudwatchMetricTask:
    ns: str
    metric_name: str
    resource_name: str
    dimensions: dict[str, str]
    statistic: str
    nil_to_zero: bool
    add_cw_timestamp: bool
    unit: str | None
    tags: dict[str, str]
    result: CloudwatchMetricResult | None = None
    signature: MetricTaskSignature = None  # type: ignore[assignment]

    def __post_init__(self):
        dims = tuple(sorted(self.dimensions.items()))
        tags = tuple(sorted(self.tags.items()))
        self.signature = (self.ns, self.metric_name, dims, tags)

    def stat_shortname(self) -> str:
        stat = self.statistic.lower()
        if stat == "samplecount":
            return "count"
        if stat == "average":
            return "avg"
        if stat == "sum":
            return "sum"
        if stat == "minimum":
            return "min"
        if stat == "maximum":
            return "max"
        return stat

    def get_timestamp(self) -> float | None:

        if not self.result:
            raise ValueError("result not set")

        if not self.add_cw_timestamp or not self.result.timestamps:
            return None

        return self.result.timestamps[0].timestamp()

    def get_value(self) -> float | int | None:
        if not self.result:
            raise ValueError("result not set")

        values = self.result.values or []

        if not values:
            return 0 if self.nil_to_zero else None

        num_values = len(values)

        if num_values == 1 or self.statistic not in (
            "Sum",
            "Minimum",
            "Maximum",
            "SampleCount",
        ):
            return values[0]

        if self.statistic in ("Sum", "SampleCount"):
            return sum(values)

        if self.statistic == "Minimum":
            return min(values)

        assert self.statistic == "Maximum"
        return max(values)


@dataclass
class MetricStats:
    ns: str
    name: str
    count: int
