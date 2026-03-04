"""Event definitions for the app state machine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Event:
    type: str
    payload: dict[str, Any] = field(default_factory=dict)


def event(type: str, **payload: Any) -> Event:
    return Event(type=type, payload=payload)
