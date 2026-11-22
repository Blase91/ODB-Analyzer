@echo off
cd /d "%~dp0"

echo Checking Tailscale status...
tailscale status >nul 2>&1
if errorlevel 1 (
    echo Tailscale is stopped. Starting Tailscale...
    tailscale up
    if errorlevel 1 (
        echo Failed to start Tailscale. Please open the Tailscale app and connect first.
        pause
        exit /b 1
    )
)

echo Configuring Tailscale Serve for port 8501...
tailscale serve --bg 8501
echo.
echo Remote VPN URL ^(open this on any device in your Tailscale tailnet^):
tailscale serve status
echo.
echo Starting Telemetry Data Analyzer on http://127.0.0.1:8501 ...
uv run streamlit run app.py
