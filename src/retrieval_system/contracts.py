"""Message contracts shared across services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4


class EventValidationError(ValueError):
    """Raised when an event does not match the required contract."""


def utc_now() -> datetime:
    """Return current UTC time with timezone info."""
    return datetime.now(timezone.utc)


def to_iso_timestamp(value: datetime) -> str:
    """Serialize datetime to RFC3339-like UTC string."""
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_timestamp(value: str) -> datetime:
    """Parse RFC3339-like string into UTC datetime."""
    if not isinstance(value, str) or not value.strip():
        raise EventValidationError("timestamp must be a non-empty string")

    raw = value.strip()
    if raw.endswith("Z"):
        raw = f"{raw[:-1]}+00:00"

    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise EventValidationError(f"invalid timestamp: {value}") from exc

    if parsed.tzinfo is None:
        raise EventValidationError("timestamp must include timezone info")

    return parsed.astimezone(timezone.utc)


def new_event_id(prefix: str = "evt") -> str:
    """Create a compact event identifier."""
    return f"{prefix}_{uuid4().hex[:12]}"


@dataclass(frozen=True)
class Event:
    """Validated pub-sub message."""

    type: str
    topic: str
    event_id: str
    payload: dict[str, Any]
    timestamp: datetime

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "Event":
        required = {"type", "topic", "event_id", "payload", "timestamp"}
        missing = required.difference(raw.keys())
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise EventValidationError(f"missing required keys: {missing_list}")

        event_type = str(raw["type"]).strip()
        if event_type != "publish":
            raise EventValidationError('type must be exactly "publish"')

        topic = str(raw["topic"]).strip()
        if not topic:
            raise EventValidationError("topic must be a non-empty string")

        event_id = str(raw["event_id"]).strip()
        if not event_id:
            raise EventValidationError("event_id must be a non-empty string")

        payload = raw["payload"]
        if not isinstance(payload, Mapping):
            raise EventValidationError("payload must be an object")

        timestamp = raw["timestamp"]
        if isinstance(timestamp, datetime):
            if timestamp.tzinfo is None:
                raise EventValidationError("timestamp datetime must be timezone-aware")
            parsed_timestamp = timestamp.astimezone(timezone.utc)
        else:
            parsed_timestamp = parse_timestamp(str(timestamp))

        return cls(
            type=event_type,
            topic=topic,
            event_id=event_id,
            payload=dict(payload),
            timestamp=parsed_timestamp,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize event back to the shared JSON-friendly schema."""
        return {
            "type": self.type,
            "topic": self.topic,
            "event_id": self.event_id,
            "payload": dict(self.payload),
            "timestamp": to_iso_timestamp(self.timestamp),
        }


def build_event(
    topic: str,
    event_id: str,
    payload: Mapping[str, Any],
    timestamp: datetime | None = None,
) -> Event:
    """Helper for creating compliant publish events."""
    return Event.from_dict(
        {
            "type": "publish",
            "topic": topic,
            "event_id": event_id,
            "payload": dict(payload),
            "timestamp": to_iso_timestamp(timestamp or utc_now()),
        }
    )
