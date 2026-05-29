#!/bin/bash
# Wait for the Streamlit dashboard to be ready, then launch Chromium fullscreen.

# Hide the mouse cursor when idle (optional, makes it feel more appliance-y)
# unclutter -idle 3 &

# Poll until the dashboard responds
until curl -sf http://localhost:8501 > /dev/null; do
    sleep 2
done

# Small extra delay so Streamlit fully initialises its UI
sleep 3

# Launch Chromium in fullscreen, pointed at the dashboard.
# --start-fullscreen lets you press F11 to exit; --kiosk would lock you in.
chromium-browser \
    --start-fullscreen \
    --noerrdialogs \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --check-for-update-interval=31536000 \
    http://localhost:8501
