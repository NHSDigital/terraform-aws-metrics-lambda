import re

from model import CloudwatchMetric, Resource

_MQ_SUFFIX = re.compile(r"-[0-9]+$")


def _fix_dimension(ns: str, dimension: str, value: str) -> tuple[str, bool]:

    if ns == "AWS/AmazonMQ" and dimension == "Broker":
        fixed = _MQ_SUFFIX.sub("", value)
        return fixed, fixed != value

    if ns == "AWS/SageMaker" and dimension in (
        "EndpointName",
        "InferenceComponentName",
    ):
        return value.lower(), True

    return value, False


def _maybe_fix_sig(
    ns: str, metric_dims: dict[str, str], mapping_dim_keys: set[str], try_fix: bool
) -> tuple[tuple[tuple[str, str], ...], bool]:
    if not try_fix or ns not in ("AWS/AmazonMQ", "AWS/SageMaker"):
        return tuple((k, metric_dims[k]) for k in mapping_dim_keys), False

    was_fixed = False
    sig_parts = []
    for k in mapping_dim_keys:
        val, fixed = _fix_dimension(ns, k, metric_dims[k])
        was_fixed = was_fixed or fixed
        sig_parts.append((k, val))

    return tuple(sig_parts), was_fixed


class Associator:

    def __init__(
        self, dimensions_regexes: list[re.Pattern[str]], resources: list[Resource]
    ):
        self.dimensions_regexes = dimensions_regexes
        self.resources = resources
        self.mappings = self.get_mappings()

    def get_mappings(
        self,
    ) -> list[tuple[set[str], dict[tuple[tuple[str, str], ...], Resource]]]:
        mappings: list[tuple[set[str], dict[tuple[tuple[str, str], ...], Resource]]] = (
            []
        )
        for rex in self.dimensions_regexes:
            dim_names: set[str] | None = None
            mapped: dict[tuple[tuple[str, str], ...], Resource] = {}
            for resource in self.resources:
                if resource.mapped:
                    continue
                match = rex.search(resource.arn)
                if not match:
                    continue
                dims = match.groupdict()
                sig = tuple(sorted(dims.items()))
                mapped[sig] = resource
                resource.mapped = True
                if dim_names is None:
                    dim_names = {a[0] for a in sig}
            if dim_names:
                mappings.append((dim_names, mapped))

        mappings.sort(key=lambda x: len(x[0]), reverse=True)
        return mappings

    def associate_metric_to_resource(
        self, metric: CloudwatchMetric
    ) -> tuple[Resource | None, bool]:

        if not metric.dimension_names:
            return None, False

        skip = False
        for mapping_dim_keys, resources in self.mappings:

            if not mapping_dim_keys.issubset(metric.dimension_names):
                continue

            skip = True

            for try_fix in (True, False):

                sig, fixed = _maybe_fix_sig(
                    metric.ns, metric.dimensions, mapping_dim_keys, try_fix
                )
                found = resources.get(sig)
                if found:
                    return found, False

                if not fixed:
                    return None, True

        return None, skip


class NoOpAssociator:

    def associate_metric_to_resource(
        self, _metric: CloudwatchMetric
    ) -> tuple[Resource | None, bool]:
        return None, False
