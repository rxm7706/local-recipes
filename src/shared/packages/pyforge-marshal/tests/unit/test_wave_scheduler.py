"""Unit tests for Story 28.16 wave batch scheduling."""

from __future__ import annotations

from pyforge.marshal.core.dispatch_fleet import WaveBatch, build_wave_batch
from pyforge.marshal.core.identity import normalize, render_feed_key


def test_serial_cap_returns_first_ready_only() -> None:
    wave = build_wave_batch(
        wave_id="w1",
        ready=("28-10-a", "28-11-b"),
        cap=1,
        surfaces={
            "28-10-a": ("src/a/**",),
            "28-11-b": ("src/b/**",),
        },
    )
    assert wave == WaveBatch(wave_id="w1", members=("28-10-a",), max_parallel=1)


def test_disjoint_surfaces_fan_out_to_cap() -> None:
    wave = build_wave_batch(
        wave_id="w2",
        ready=("28-10-a", "28-11-b", "28-12-c"),
        cap=2,
        surfaces={
            "28-10-a": ("src/a/**",),
            "28-11-b": ("src/b/**",),
            "28-12-c": ("src/c/**",),
        },
    )
    assert wave.members == ("28-10-a", "28-11-b")
    assert wave.refused[0].story == "28-12-c"
    assert wave.refused[0].reason == "cap"


def test_overlapping_surface_refused_with_evidence() -> None:
    wave = build_wave_batch(
        wave_id="w3",
        ready=("28-10-a", "28-11-b"),
        cap=2,
        surfaces={
            "28-10-a": ("src/shared/**",),
            "28-11-b": ("src/shared/packages/**",),
        },
    )
    assert wave.members == ("28-10-a",)
    assert len(wave.refused) == 1
    assert wave.refused[0].reason == "surface-overlap"
    assert wave.refused[0].overlap_with == "28-10-a"
    assert wave.refused[0].paths


def test_unknown_surface_never_batches() -> None:
    wave = build_wave_batch(
        wave_id="w4",
        ready=("28-10-a", "28-11-b"),
        cap=2,
        surfaces={
            "28-10-a": ("src/a/**",),
            "28-11-b": None,
        },
    )
    assert wave.members == ("28-10-a",)
    assert wave.refused[0].reason == "unknown-surface"


def test_dep_edge_refuses_same_wave_member() -> None:
    dep = render_feed_key(normalize("28.12"))
    child = render_feed_key(normalize("28.16"))
    wave = build_wave_batch(
        wave_id="w5",
        ready=(dep, child),
        cap=2,
        surfaces={
            dep: ("src/a/**",),
            child: ("src/b/**",),
        },
        deps_graph={child: (normalize("28.12"),), dep: ()},
    )
    assert wave.members == (dep,)
    assert wave.refused[0].reason == "dep-unmet"
