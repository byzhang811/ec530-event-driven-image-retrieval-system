"""Deterministic vector helpers for simulation and tests."""

from __future__ import annotations

import hashlib
import math
from typing import Iterable


def text_to_vector(text: str, dims: int = 16) -> list[float]:
    """Map text to a deterministic pseudo-embedding."""
    seed = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    while len(values) < dims:
        seed = hashlib.sha256(seed).digest()
        for i in range(0, len(seed), 4):
            chunk = seed[i : i + 4]
            if len(chunk) < 4:
                continue
            num = int.from_bytes(chunk, "big") / 0xFFFFFFFF
            values.append((num * 2.0) - 1.0)
            if len(values) == dims:
                break
    return normalize(values)


def normalize(vector: Iterable[float]) -> list[float]:
    vec = [float(v) for v in vector]
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return [0.0 for _ in vec]
    return [v / norm for v in vec]


def cosine_similarity(a: Iterable[float], b: Iterable[float]) -> float:
    left = list(a)
    right = list(b)
    if len(left) != len(right) or not left:
        return 0.0
    numerator = sum(x * y for x, y in zip(left, right))
    left_norm = math.sqrt(sum(x * x for x in left))
    right_norm = math.sqrt(sum(y * y for y in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)
