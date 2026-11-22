"""Interactive Plotly visualization and summary helpers for telemetry data."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def format_channel_label(channel: str, units_map: dict[str, str]) -> str:
    """Format a channel name with its unit if available."""
    unit = units_map.get(channel, "")
    return f"{channel} ({unit})" if unit else channel


def compute_time_axis(
    index: pd.Index,
    time_unit: str,
) -> tuple[pd.Series | pd.Index, str]:
    """Convert raw SECONDS index into the requested display time axis."""
    if index.empty:
        return index, time_unit
    t0 = index.min()
    if time_unit == "Elapsed Minutes":
        return (index - t0) / 60.0, "Elapsed Time (min)"
    if time_unit == "Elapsed Seconds":
        return index - t0, "Elapsed Time (s)"
    return index, "SECONDS"


def _prepare_series(
    df_pivot: pd.DataFrame,
    channel: str,
    gap_mode: str,
    time_unit: str,
) -> tuple[pd.Series | pd.Index, pd.Series, str]:
    """Prepare x, y values and Plotly trace mode for a single channel."""
    series = df_pivot[channel]
    if gap_mode == "Forward-fill":
        filled = series.ffill().dropna()
        x, _ = compute_time_axis(filled.index, time_unit)
        return x, filled, "lines"
    clean = series.dropna()
    x, _ = compute_time_axis(clean.index, time_unit)
    mode = "markers" if gap_mode == "Markers only" else "lines"
    return x, clean, mode


def build_telemetry_figure(
    df_pivot: pd.DataFrame,
    units_map: dict[str, str],
    primary_channels: list[str],
    secondary_channels: list[str] | None = None,
    gap_mode: str = "Connect (drop NaNs)",
    time_unit: str = "Elapsed Minutes",
) -> go.Figure:
    """Build an interactive dual-axis Plotly time-series figure for selected channels."""
    secondary_channels = secondary_channels or []
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    for ch in primary_channels:
        if ch not in df_pivot.columns:
            continue
        x, y, mode = _prepare_series(df_pivot, ch, gap_mode, time_unit)
        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode=mode,
                name=format_channel_label(ch, units_map),
                marker={"size": 4} if mode == "markers" else None,
            ),
            secondary_y=False,
        )

    for ch in secondary_channels:
        if ch not in df_pivot.columns:
            continue
        x, y, mode = _prepare_series(df_pivot, ch, gap_mode, time_unit)
        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode=mode,
                name=f"{format_channel_label(ch, units_map)} [Right]",
                line={"dash": "dot"} if mode == "lines" else None,
                marker={"size": 4} if mode == "markers" else None,
            ),
            secondary_y=True,
        )

    _, x_title = compute_time_axis(df_pivot.index, time_unit)
    primary_title = (
        ", ".join(format_channel_label(c, units_map) for c in primary_channels[:2])
        + (" ..." if len(primary_channels) > 2 else "")
        if primary_channels
        else "Primary Y"
    )
    secondary_title = (
        ", ".join(format_channel_label(c, units_map) for c in secondary_channels[:2])
        + (" ..." if len(secondary_channels) > 2 else "")
        if secondary_channels
        else "Secondary Y"
    )

    fig.update_layout(
        height=600,
        hovermode="x unified",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0},
        margin={"l": 60, "r": 60, "t": 60, "b": 40},
        xaxis={
            "title": x_title,
            "rangeslider": {"visible": True},
        },
    )
    fig.update_yaxes(title_text=primary_title, secondary_y=False)
    fig.update_yaxes(
        title_text=secondary_title,
        secondary_y=True,
        showgrid=False,
        visible=bool(secondary_channels),
    )
    return fig


def build_summary_table(
    df_pivot: pd.DataFrame,
    units_map: dict[str, str],
    channels: list[str],
) -> pd.DataFrame:
    """Compute summary statistics for the selected telemetry channels."""
    rows = []
    for ch in channels:
        if ch not in df_pivot.columns:
            continue
        s = df_pivot[ch].dropna()
        if s.empty:
            continue
        rows.append(
            {
                "Channel": ch,
                "Unit": units_map.get(ch, ""),
                "Samples": int(s.count()),
                "Min": round(float(s.min()), 4),
                "Mean": round(float(s.mean()), 4),
                "Max": round(float(s.max()), 4),
                "Latest": round(float(s.iloc[-1]), 4),
            }
        )
    return pd.DataFrame(rows)
