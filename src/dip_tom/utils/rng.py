"""Randomness utilities for deterministic experiments."""

from __future__ import annotations

import random


def set_global_seed(seed: int) -> None:
    """Seed the module-level RNG for deterministic behavior."""
    random.seed(seed)


def make_rng(seed: int) -> random.Random:
    """Create a dedicated RNG seeded for deterministic behavior."""
    return random.Random(seed)
