"""Event bus abstractions and adapters."""

from __future__ import annotations

import json
import threading
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Protocol
from uuid import uuid4

from .contracts import Event, EventValidationError

EventHandler = Callable[[Event], None]


class EventBus(Protocol):
    """Shared interface for event bus implementations."""

    def subscribe(self, topic: str, handler: EventHandler, name: str | None = None) -> str:
        ...

    def publish(self, event: Event, delay_steps: int = 0) -> None:
        ...

    def publish_raw(self, raw_event: dict, delay_steps: int = 0) -> bool:
        ...


@dataclass
class _Subscriber:
    topic: str
    handler: EventHandler
    active: bool
    name: str


class InMemoryEventBus:
    """Synchronous in-memory bus for local runs and deterministic tests."""

    def __init__(self) -> None:
        self._topic_index: dict[str, list[str]] = defaultdict(list)
        self._subscribers: dict[str, _Subscriber] = {}
        self._delayed: list[tuple[int, Event]] = []
        self.dropped_topics: set[str] = set()
        self.rejected_events: list[dict] = []
        self.handler_errors: list[dict] = []

    def subscribe(self, topic: str, handler: EventHandler, name: str | None = None) -> str:
        token = f"sub_{uuid4().hex[:12]}"
        self._subscribers[token] = _Subscriber(
            topic=topic,
            handler=handler,
            active=True,
            name=name or token,
        )
        self._topic_index[topic].append(token)
        return token

    def unsubscribe(self, token: str) -> None:
        subscriber = self._subscribers.pop(token, None)
        if subscriber is None:
            return
        topic_tokens = self._topic_index.get(subscriber.topic, [])
        self._topic_index[subscriber.topic] = [t for t in topic_tokens if t != token]

    def pause_subscription(self, token: str) -> None:
        if token in self._subscribers:
            self._subscribers[token].active = False

    def resume_subscription(self, token: str) -> None:
        if token in self._subscribers:
            self._subscribers[token].active = True

    def set_topic_drop(self, topic: str, enabled: bool = True) -> None:
        if enabled:
            self.dropped_topics.add(topic)
        else:
            self.dropped_topics.discard(topic)

    def publish(self, event: Event, delay_steps: int = 0) -> None:
        if delay_steps > 0:
            self._delayed.append((delay_steps, event))
            return
        self._dispatch(event)

    def publish_raw(self, raw_event: dict, delay_steps: int = 0) -> bool:
        try:
            event = Event.from_dict(raw_event)
        except EventValidationError as exc:
            self.rejected_events.append({"event": raw_event, "error": str(exc)})
            return False

        self.publish(event, delay_steps=delay_steps)
        return True

    def tick(self, steps: int = 1) -> None:
        for _ in range(steps):
            still_waiting: list[tuple[int, Event]] = []
            for remaining_steps, event in self._delayed:
                next_step = remaining_steps - 1
                if next_step <= 0:
                    self._dispatch(event)
                else:
                    still_waiting.append((next_step, event))
            self._delayed = still_waiting

    def _dispatch(self, event: Event) -> None:
        if event.topic in self.dropped_topics:
            return

        for token in list(self._topic_index.get(event.topic, [])):
            subscriber = self._subscribers.get(token)
            if subscriber is None or not subscriber.active:
                continue
            try:
                subscriber.handler(event)
            except Exception as exc:  # pragma: no cover - defensive path
                self.handler_errors.append(
                    {
                        "subscription": subscriber.name,
                        "topic": event.topic,
                        "event_id": event.event_id,
                        "error": str(exc),
                    }
                )


class RedisEventBus:
    """Redis pub-sub adapter for real broker runs."""

    def __init__(self, url: str = "redis://localhost:6379/0") -> None:
        try:
            import redis  # type: ignore
        except Exception as exc:  # pragma: no cover - depends on local env
            raise RuntimeError(
                "redis package is required for RedisEventBus. "
                "Install with: pip install redis"
            ) from exc

        self._redis = redis.Redis.from_url(url, decode_responses=True)
        self._subs: dict[str, tuple[object, threading.Thread]] = {}
        self.rejected_events: list[dict] = []
        self.handler_errors: list[dict] = []
        self._closing = False

    def subscribe(self, topic: str, handler: EventHandler, name: str | None = None) -> str:
        token = f"redis_sub_{uuid4().hex[:12]}"
        pubsub = self._redis.pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe(topic)

        def _listen() -> None:
            while not self._closing:
                try:
                    message = pubsub.get_message(ignore_subscribe_messages=True, timeout=0.2)
                except Exception as exc:  # pragma: no cover - defensive path
                    if self._closing:
                        break
                    self.handler_errors.append(
                        {
                            "subscription": name or token,
                            "topic": topic,
                            "event_id": "unknown",
                            "error": str(exc),
                        }
                    )
                    continue

                if message is None or message.get("type") != "message":
                    continue
                raw = message.get("data")
                if raw is None:
                    continue
                try:
                    event = Event.from_dict(json.loads(raw))
                except Exception as exc:  # pragma: no cover - defensive path
                    self.rejected_events.append({"event": raw, "error": str(exc)})
                    continue
                try:
                    handler(event)
                except Exception as exc:  # pragma: no cover - defensive path
                    self.handler_errors.append(
                        {
                            "subscription": name or token,
                            "topic": topic,
                            "event_id": getattr(event, "event_id", "unknown"),
                            "error": str(exc),
                        }
                    )

        thread = threading.Thread(
            target=_listen,
            daemon=True,
            name=name or token,
        )
        thread.start()
        self._subs[token] = (pubsub, thread)
        return token

    def publish(self, event: Event, delay_steps: int = 0) -> None:
        if delay_steps:
            raise ValueError("RedisEventBus does not support delay_steps")
        self._redis.publish(event.topic, json.dumps(event.to_dict()))

    def publish_raw(self, raw_event: dict, delay_steps: int = 0) -> bool:
        try:
            event = Event.from_dict(raw_event)
        except EventValidationError as exc:
            self.rejected_events.append({"event": raw_event, "error": str(exc)})
            return False
        self.publish(event, delay_steps=delay_steps)
        return True

    def close(self) -> None:
        self._closing = True
        for _token, (pubsub, thread) in self._subs.items():
            try:
                pubsub.close()
            except Exception:  # pragma: no cover - defensive cleanup
                pass
            if thread.is_alive():
                thread.join(timeout=0.5)
        self._subs.clear()
