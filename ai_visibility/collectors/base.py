from __future__ import annotations

import abc
import dataclasses
from dataclasses import field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from decimal import Decimal


@dataclasses.dataclass
class MetricValue:
    """One metric value produced by a collector for the current period."""

    metric_key: str
    value: Decimal
    dimensions: dict = field(default_factory=dict)


class BaseCollector(abc.ABC):
    """Base class for pluggable metric collectors.

    Subclass, set ``provider`` and ``metrics_produced``, implement ``collect``,
    and decorate with ``@register`` to make it discoverable.
    """

    provider: str
    metrics_produced: list[str]

    def __init__(self, team, integration):
        self.team = team
        self.integration = integration

    @abc.abstractmethod
    def collect(self, period_start, period_end) -> list[MetricValue]:
        """Return metric values for the given period."""


REGISTRY: dict[str, type[BaseCollector]] = {}


def register(cls: type[BaseCollector]) -> type[BaseCollector]:
    """Class decorator that registers a collector by its ``provider``."""
    REGISTRY[cls.provider] = cls
    return cls
