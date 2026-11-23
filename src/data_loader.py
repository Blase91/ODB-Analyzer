"""Data loading and pivoting utilities for OBD-II / GPS telemetry CSV logs."""

from __future__ import annotations

from pathlib import Path
from typing import IO

import pandas as pd


def load_telemetry_csv(
    source: str | Path | IO[bytes] | IO[str],
) -> tuple[pd.DataFrame, dict[str, str]]:
    """Load a semicolon-delimited telemetry CSV and pivot it by SECONDS and PID.

    Args:
        source: File path or file-like object containing ``SECONDS;PID;VALUE;UNITS;`` data.

    Returns:
        A tuple of ``(df_pivot, units_map)`` where ``df_pivot`` is indexed by
        sorted ``SECONDS`` with ``PID`` names as columns, and ``units_map`` maps
        each ``PID`` to its unit string (empty string if missing).

    Raises:
        ValueError: If required columns (``SECONDS``, ``PID``, ``VALUE``) are absent.
    """
    df = pd.read_csv(source, sep=";")
    unnamed_cols = [c for c in df.columns if str(c).startswith("Unnamed:")]
    if unnamed_cols:
        df = df.drop(columns=unnamed_cols)

    required = {"SECONDS", "PID", "VALUE"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {sorted(missing)}")

    df["SECONDS"] = pd.to_numeric(df["SECONDS"], errors="coerce")
    df["VALUE"] = pd.to_numeric(df["VALUE"], errors="coerce")
    df = df.dropna(subset=["SECONDS", "PID", "VALUE"])

    units_map: dict[str, str] = {}
    if "UNITS" in df.columns:
        for pid, group in df.groupby("PID", sort=False):
            non_null = group["UNITS"].dropna().astype(str).str.strip()
            non_empty = non_null[non_null != ""]
            units_map[str(pid)] = non_empty.iloc[0] if not non_empty.empty else ""
    else:
        for pid in df["PID"].unique():
            units_map[str(pid)] = ""

    df_pivot = df.pivot_table(
        values="VALUE",
        columns="PID",
        index="SECONDS",
        aggfunc="mean",
    ).sort_index()

    return df_pivot, units_map


def get_channel_presets(columns: list[str]) -> dict[str, dict[str, list[str]]]:
    """Return preset primary/secondary channel selections matching available columns."""
    col_set = set(columns)
    candidates: dict[str, dict[str, list[str]]] = {
        "Speed & GPS": {
            "primary": [c for c in ["Vehicle speed", "Speed (GPS)", "Average speed"] if c in col_set],
            "secondary": [c for c in ["Altitude (GPS)"] if c in col_set],
        },
        "Engine & Boost": {
            "primary": [c for c in ["Calculated engine load value"] if c in col_set],
            "secondary": [c for c in ["Calculated boost", "Intake manifold absolute pressure"] if c in col_set],
        },
        "Misfires": {
            "primary": [
                c
                for c in columns
                if "catalyst damaging misfires" in c.lower() and "#" in c
            ],
            "secondary": [c for c in ["Calculated engine load value"] if c in col_set],
        },
        "Distance": {
            "primary": [c for c in columns if "distance" in c.lower()],
            "secondary": [],
        },
    }
    return {
        name: cfg
        for name, cfg in candidates.items()
        if cfg["primary"] or cfg["secondary"]
    }
