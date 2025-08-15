import json
import os

from model import DiscoveryJob, MetricRequest, StaticJob
from services import _SERVICES_CONF, _Services


class ScrapeConfig:

    def __init__(
        self,
        config: str | None = None,
        rtf_overrides: dict[str, list[str]] | None = None,
    ):

        config = config or os.environ.get("SCRAPE_CONFIG", "{}")
        assert config
        self._services: _Services = _Services(_SERVICES_CONF)
        self._rtf_overrides = rtf_overrides or {}
        self._config = json.loads(config)
        self.default_region = self._config.get("default-region", "eu-west-2")
        self.sts_region = self._config.get("sts-region", self.default_region)
        self.boto_kwargs = self._boto_config_base()
        self._discovery = self._config.get("discovery", {})
        self._static = self._config.get("static", {})
        self.discovery_jobs: list[DiscoveryJob] = self._get_discovery_jobs()
        self.static_jobs: list[StaticJob] = self._get_static_jobs()

    def _boto_config_base(self) -> dict:
        cfg = self._config.get("boto-config", {})
        kwargs = {
            "region_name": self.default_region,
            "connect_timeout": float(cfg.get("connect_timeout", 1)),
            "read_timeout": float(cfg.get("read_timeout", 5)),
        }

        return kwargs

    def _get_discovery_jobs(self) -> list[DiscoveryJob]:

        cfg = self._discovery.get("jobs", [])
        if not cfg:
            return []
        exported_tags = {t for t in self._discovery.get("exported_tags", []) if t}
        jobs: list[DiscoveryJob] = []
        for raw in cfg:
            try:
                svc = self._services.get(raw.pop("type"))
                raw["ns"] = svc.ns
                raw["metrics"] = [MetricRequest(**m) for m in raw["metrics"]]
                raw["dimensions_regexps"] = svc.rex
                raw["exported_tags"] = exported_tags
                job = DiscoveryJob(**raw)
                jobs.append(job)
            except Exception as e:
                raise ValueError(f"error parsing: {raw}") from e

        return jobs

    def _get_static_jobs(self) -> list[StaticJob]:

        cfg = self._static.get("jobs", [])
        if not cfg:
            return []

        jobs: list[StaticJob] = []
        for raw in cfg:
            try:
                svc = self._services.get(raw.pop("type"))
                raw["ns"] = svc.ns
                raw["metrics"] = [MetricRequest(**m) for m in raw["metrics"]]
                job = StaticJob(**raw)
                jobs.append(job)
            except Exception as e:
                raise ValueError(f"error parsing: {raw}") from e

        return jobs
