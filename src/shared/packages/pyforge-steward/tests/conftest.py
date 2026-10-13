"""Shared pytest fixtures for pyforge-steward tests."""

from __future__ import annotations

from pyforge.testing_kit import make_flag_provider_fixture

flag_provider = make_flag_provider_fixture()
