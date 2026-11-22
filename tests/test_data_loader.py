"""Unit tests for telemetry data loading and visualization helpers."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from src.data_loader import get_channel_presets, load_telemetry_csv
from src.plotting import build_summary_table, build_telemetry_figure

SAMPLE_CSV = Path(__file__).resolve().parent.parent / "2026-11-22 09-14-55.csv"


def test_load_sample_csv_shape_and_units():
    df_pivot, units_map = load_telemetry_csv(SAMPLE_CSV)
    assert df_pivot.shape == (4685, 29)
    assert df_pivot.index.is_monotonic_increasing
    assert units_map["Calculated boost"] == "bar"
    assert units_map["Vehicle speed"] == "km/h"
    assert units_map["[ECM] Misfires current #1"] == ""


def test_load_missing_columns_raises():
    bad_csv = io.StringIO("A;B;C\n1;2;3\n")
    with pytest.raises(ValueError, match="missing required columns"):
        load_telemetry_csv(bad_csv)


def test_presets_and_figure_generation():
    df_pivot, units_map = load_telemetry_csv(SAMPLE_CSV)
    presets = get_channel_presets([str(c) for c in df_pivot.columns])
    assert "Speed & GPS" in presets
    assert "Engine & Boost" in presets

    fig = build_telemetry_figure(
        df_pivot=df_pivot,
        units_map=units_map,
        primary_channels=["Vehicle speed"],
        secondary_channels=["Calculated boost"],
        gap_mode="Connect (drop NaNs)",
        time_unit="Elapsed Minutes",
    )
    assert len(fig.data) == 2
    assert fig.data[0].name == "Vehicle speed (km/h)"
    assert fig.data[1].name == "Calculated boost (bar) [Right]"

    summary = build_summary_table(df_pivot, units_map, ["Vehicle speed", "Calculated boost"])
    assert list(summary["Channel"]) == ["Vehicle speed", "Calculated boost"]
    assert summary.loc[0, "Samples"] > 0
