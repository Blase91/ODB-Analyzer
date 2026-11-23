"""Streamlit application for interactive OBD-II / GPS telemetry analysis."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.data_loader import get_catalyst_misfire_channels, get_channel_presets, load_telemetry_csv
from src.plotting import (
    build_misfire_breakdown_figure,
    build_summary_table,
    build_telemetry_figure,
    format_channel_label,
)

st.set_page_config(page_title="Telemetry Data Analyzer", layout="wide")
st.title("Telemetry Data Analyzer")


@st.cache_data(show_spinner="Loading and pivoting telemetry CSV...")
def _load_cached_bytes(file_bytes: bytes, file_name: str):
    import io

    return load_telemetry_csv(io.BytesIO(file_bytes))


@st.cache_data(show_spinner="Loading and pivoting telemetry CSV...")
def _load_cached_path(path_str: str):
    return load_telemetry_csv(Path(path_str))


def _discover_workspace_csvs() -> list[Path]:
    csvs = list(Path(".").glob("*.csv")) + list((Path("src") / "example_data").glob("*.csv"))
    return sorted(dict.fromkeys(csvs))


with st.sidebar:
    st.header("1. Data Source")
    uploaded_file = st.file_uploader("Upload telemetry CSV", type=["csv"])
    workspace_csvs = _discover_workspace_csvs()

    df_pivot = None
    units_map: dict[str, str] = {}
    active_name = ""

    if uploaded_file is not None:
        df_pivot, units_map = _load_cached_bytes(uploaded_file.getvalue(), uploaded_file.name)
        active_name = uploaded_file.name
    elif workspace_csvs:
        selected_path = st.selectbox(
            "Or select a CSV in workspace",
            options=workspace_csvs,
            format_func=lambda p: p.name,
        )
        if selected_path is not None:
            df_pivot, units_map = _load_cached_path(str(selected_path))
            active_name = selected_path.name

if df_pivot is None or df_pivot.empty:
    st.info("Upload a semicolon-delimited telemetry CSV (`SECONDS;PID;VALUE;UNITS;`) to begin.")
    st.stop()

all_channels = [str(c) for c in df_pivot.columns]
presets = get_channel_presets(all_channels)

if "primary_channels" not in st.session_state:
    default_preset = next(iter(presets.values()), {"primary": all_channels[:2], "secondary": []})
    st.session_state.primary_channels = default_preset["primary"]
    st.session_state.secondary_channels = default_preset["secondary"]

# Keep session state valid if a different CSV with different columns is loaded
st.session_state.primary_channels = [c for c in st.session_state.primary_channels if c in all_channels]
st.session_state.secondary_channels = [c for c in st.session_state.secondary_channels if c in all_channels]

with st.sidebar:
    st.header("2. Channel Presets")
    if presets:
        preset_cols = st.columns(2)
        for idx, (preset_name, cfg) in enumerate(presets.items()):
            if preset_cols[idx % 2].button(preset_name, width="stretch"):
                st.session_state.primary_channels = cfg["primary"]
                st.session_state.secondary_channels = cfg["secondary"]

    st.header("3. Channel Selection")
    primary_channels = st.multiselect(
        "Primary Y-Axis (Left)",
        options=all_channels,
        key="primary_channels",
        format_func=lambda c: format_channel_label(c, units_map),
    )
    secondary_channels = st.multiselect(
        "Secondary Y-Axis (Right, optional)",
        options=all_channels,
        key="secondary_channels",
        format_func=lambda c: format_channel_label(c, units_map),
    )

    st.header("4. Plot Options")
    time_unit = st.selectbox(
        "Time Axis",
        options=["Absolute Time (HH:MM:SS)", "Elapsed Minutes", "Elapsed Seconds", "Raw SECONDS"],
        index=0,
    )
    gap_mode = st.selectbox(
        "NaN Handling",
        options=["Connect (drop NaNs)", "Forward-fill", "Markers only"],
        index=0,
    )

duration_min = (df_pivot.index.max() - df_pivot.index.min()) / 60.0
m1, m2, m3, m4 = st.columns(4)
m1.metric("Active File", active_name)
m2.metric("Duration", f"{duration_min:.1f} min")
m3.metric("Timestamps", f"{len(df_pivot):,}")
m4.metric("Available Channels", len(all_channels))

selected_all = list(dict.fromkeys(primary_channels + secondary_channels))

tab_explorer, tab_misfires = st.tabs(["Telemetry Explorer", "Misfire Analysis"])

with tab_explorer:
    if not selected_all:
        st.warning("Select at least one channel from the sidebar dropdowns to display a chart.")
    else:
        fig = build_telemetry_figure(
            df_pivot=df_pivot,
            units_map=units_map,
            primary_channels=primary_channels,
            secondary_channels=secondary_channels,
            gap_mode=gap_mode,
            time_unit=time_unit,
        )
        st.plotly_chart(fig, width="stretch")

        st.subheader("Summary Statistics")
        summary_df = build_summary_table(df_pivot, units_map, selected_all)
        st.dataframe(summary_df, width="stretch", hide_index=True)

        export_csv = df_pivot[selected_all].to_csv().encode("utf-8")
        st.download_button(
            label="Download Selected Channels (Pivoted CSV)",
            data=export_csv,
            file_name=f"filtered_{Path(active_name).stem}.csv",
            mime="text/csv",
        )

with tab_misfires:
    misfire_cols = get_catalyst_misfire_channels(all_channels)
    if not misfire_cols:
        st.info("No per-cylinder catalyst damaging misfire channels found in this dataset.")
    else:
        misfire_fig = build_misfire_breakdown_figure(
            df_pivot=df_pivot,
            misfire_channels=misfire_cols,
            time_unit=time_unit,
        )
        st.plotly_chart(misfire_fig, width="stretch")
