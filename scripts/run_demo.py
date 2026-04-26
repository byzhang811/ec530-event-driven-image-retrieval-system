#!/usr/bin/env python3
"""Run a short end-to-end demo of the retrieval system."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from retrieval_system.bus import InMemoryEventBus, RedisEventBus
from retrieval_system.system import RetrievalSystem


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--broker",
        choices=("memory", "redis"),
        default="memory",
        help="Event bus backend.",
    )
    parser.add_argument(
        "--redis-url",
        default="redis://localhost:6379/0",
        help="Redis connection URL when --broker redis.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    bus = InMemoryEventBus() if args.broker == "memory" else RedisEventBus(args.redis_url)

    system = RetrievalSystem(bus=bus)
    try:
        system.submit_image(image_id="img_demo_1", path="images/demo_1.jpg", source="camera_A")
        system.submit_image(image_id="img_demo_2", path="images/demo_2.jpg", source="camera_B")
        system.submit_image(image_id="img_demo_3", path="images/demo_3.jpg", source="camera_A")

        # Redis pub-sub is asynchronous, so wait briefly for index convergence.
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            if system.vector_index_service.count() >= 3:
                break
            time.sleep(0.02)

        text_result = system.search_text("red car on street", top_k=3)
        image_result = system.search_image("img_demo_1", top_k=3)

        print("Text Query Result:")
        print(json.dumps(text_result, indent=2, ensure_ascii=False))
        print("\nImage Query Result:")
        print(json.dumps(image_result, indent=2, ensure_ascii=False))
    finally:
        if isinstance(bus, RedisEventBus):
            bus.close()


if __name__ == "__main__":
    main()
