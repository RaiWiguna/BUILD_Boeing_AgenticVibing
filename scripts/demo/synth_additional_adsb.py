"""Controlled centre-point fixtures for the five additional cases, never real ADS-B.

They illustrate separate entities and missing physical eligibility. No footprint,
occupancy verdict or altitude-conformance result is derived from these profiles.
"""

from __future__ import annotations

import math

# entity, start xy, end xy; all geometry is an authored fixture assumption.
PROFILES = {
    50: [("Quebec?", (-900, 350), (-300, 400)), ("Alpha?", (200, -220), (380, -200))],
    51: [("Quebec?", (-480, 330), (120, 30)), ("Alpha?", (300, 160), (950, 380))],
    47: [("Uniform?", (-47, -108), (-47, -108))],
    156: [
        ("Julia Charlie?", (260, -260), (260, -260)),
        ("Kilo Alpha?", (350, 150), (1000, 380)),
    ],
    123: [("936?", (350, 180), (1100, 400))],
}


def fixes(part: int, duration_seconds: float):
    for index, (entity, a, b) in enumerate(PROFILES[part]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        heading = math.degrees(math.atan2(dx, dy)) % 360 if dx or dy else 0
        speed = math.hypot(dx, dy) / duration_seconds / 0.514444
        for t in range(math.floor(duration_seconds) + 1):
            f = t / duration_seconds
            yield (
                entity,
                0xABC000 + part * 3 + index,
                t,
                a[0] + dx * f,
                a[1] + dy * f,
                heading,
                speed,
            )
