"""Bounded replay controls; supplied source manifests are assertions to verify, not sources."""

import json
from pathlib import Path
from typing import Any

from pydantic import Field

from packages.backtest.constrained import PortfolioPolicy
from packages.research.discovery import DiscoveryPolicy
from packages.research.event_paths import EventPathPolicy
from packages.shared.models import Record


class ReplayConfig(Record):
    discovery: DiscoveryPolicy = Field(default_factory=DiscoveryPolicy)
    portfolio: PortfolioPolicy = Field(default_factory=PortfolioPolicy)
    event: EventPathPolicy = Field(default_factory=EventPathPolicy)


def read_object(path: Path) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate replay input key")
            result[key] = value
        return result

    with path.open("rb") as stream:
        body = stream.read(65537)
    if len(body) > 65536:
        raise ValueError("Replay input exceeds size budget")
    result = json.loads(
        body,
        object_pairs_hook=unique,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Nonfinite replay input")),
    )
    if not isinstance(result, dict):
        raise ValueError("Replay input must be an object")
    return result


def verify_manifest(path: Path | None, expected: dict[str, Any]) -> None:
    if path is not None and read_object(path) != expected:
        raise ValueError("Supplied manifest differs from the generated fixture source")
