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
    assert presets["Misfires"] == {
        "primary": [
            "[ECM] Catalyst damaging Misfires total #1",
            "[ECM] Catalyst damaging Misfires total #2",
            "[ECM] Catalyst damaging Misfires total #3",
            "[ECM] Catalyst damaging Misfires total #4",
        ],
        "secondary": ["Calculated engine load value"],
    }

    fig = build_telemetry_figure(
        df_pivot=df_pivot,
        units_map=units_map,
        primary_channels=["Vehicle speed"],
        secondary_channels=["Calculated boost"],
        gap_mode="Connect (drop NaNs)",
    )
    assert len(fig.data) == 2
    assert fig.data[0].name == "Vehicle speed (km/h)"
    assert fig.data[1].name == "Calculated boost (bar) [Right]"
    assert fig.layout.xaxis.title.text == "Absolute Time (HH:MM:SS)"
    assert fig.layout.xaxis.tickformat == "%H:%M:%S"

    summary = build_summary_table(df_pivot, units_map, ["Vehicle speed", "Calculated boost"])
    assert list(summary["Channel"]) == ["Vehicle speed", "Calculated boost"]
    assert summary.loc[0, "Samples"] > 0


def test_elapsed_time_uses_global_t0():
    import pandas as pd

    df_pivot = pd.DataFrame(
        {
            "A": [1.0, float("nan"), 3.0],
            "B": [float("nan"), 20.0, 30.0],
        },
        index=pd.Index([100.0, 160.0, 220.0], name="SECONDS"),
    )
    fig = build_telemetry_figure(
        df_pivot=df_pivot,
        units_map={"A": "", "B": ""},
        primary_channels=["A", "B"],
        time_unit="Elapsed Minutes",
    )
    assert list(fig.data[0].x) == [0.0, 2.0]
    assert list(fig.data[1].x) == [1.0, 2.0]
