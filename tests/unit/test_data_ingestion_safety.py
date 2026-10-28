from __future__ import annotations

import math

import pytest

from scripts.data import load_unlocode_supabase
from scripts.data.load_wpi_supabase import normalize_feature, positive_number


@pytest.mark.parametrize(
    "value, expected",
    [
        (None, None),
        ("", None),
        ("n/a", None),
        (0, None),
        (-1, None),
        ("-2.5", None),
        ("nan", None),
        ("inf", None),
        ("+inf", None),
        ("-inf", None),
        (float("nan"), None),
        (float("inf"), None),
        (float("-inf"), None),
        ("12.5", 12.5),
        (12, 12.0),
    ],
)
def test_wpi_positive_number_returns_only_finite_positive_values(value, expected):
    assert positive_number(value) == expected


def test_wpi_feature_does_not_preserve_infinite_vessel_constraints():
    record = normalize_feature(
        {
            "attributes": {
                "wpinumber": 1234,
                "main_port_name": "Example Port",
                "maxvessellength": "inf",
                "maxvesselbeam": "NaN",
                "maxvesseldraft": "120.5",
                "channel_depth": "-inf",
            }
        }
    )

    assert record["max_loa_m"] is None
    assert record["max_beam_m"] is None
    assert record["max_draft_m"] == 120.5
    assert record["channel_depth_m"] is None


def test_unlocode_loader_refuses_publishable_key_for_privileged_writes(monkeypatch):
    monkeypatch.setattr(load_unlocode_supabase, "load_env", lambda: None)
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_test_only")

    with pytest.raises(RuntimeError, match="SUPABASE_SECRET_KEY is required"):
        load_unlocode_supabase.Supabase()


def test_unlocode_loader_prefers_secret_key_for_bulk_writes(monkeypatch):
    monkeypatch.setattr(load_unlocode_supabase, "load_env", lambda: None)
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "server-only-test-secret")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_test_only")

    client = load_unlocode_supabase.Supabase()

    assert client.key == "server-only-test-secret"
    assert client.base == "https://example.supabase.co/rest/v1"
