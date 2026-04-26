"""Deterministic and replayable event generation for testing."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from .bus import EventBus
from .contracts import Event, build_event
from .topics import IMAGE_SUBMITTED


@dataclass
class EventGenerator:
    seed: int = 42
    start_time: datetime = datetime(2026, 4, 7, 14, 33, 0, tzinfo=timezone.utc)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)
        self._counter = 0
        self._clock = self.start_time

    def generate_image_submitted_events(self, count: int) -> list[Event]:
        events: list[Event] = []
        for _ in range(count):
            self._counter += 1
            image_num = self._rng.randint(1000, 9999)
            image_id = f"img_{image_num}"
            event_id = f"evt_{image_num}_{self._counter}"
            timestamp = self._clock
            self._clock += timedelta(seconds=1)
            events.append(
                build_event(
                    topic=IMAGE_SUBMITTED,
                    event_id=event_id,
                    payload={
                        "image_id": image_id,
                        "path": f"images/street_{image_num}.jpg",
                        "source": "camera_A",
                        "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
                    },
                    timestamp=timestamp,
                )
            )
        return events

    @staticmethod
    def publish(events: Iterable[Event], bus: EventBus, delay_steps: int = 0) -> None:
        for event in events:
            bus.publish(event, delay_steps=delay_steps)

    @staticmethod
    def replay_from_jsonl(path: str | Path) -> list[Event]:
        events: list[Event] = []
        path_obj = Path(path)
        for line in path_obj.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            events.append(Event.from_dict(json.loads(line)))
        return events
