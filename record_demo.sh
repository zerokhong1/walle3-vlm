#!/bin/bash
# record_demo.sh — Record WallE3 v2 demo GIF
#
# Usage:
#   ./record_demo.sh                  # full auto: start sim + record + convert
#   ./record_demo.sh --sim-already-up # skip sim startup, just record
#
# Output: docs/media/demo_v4.gif (1280x480, left=Gazebo, right=RViz2)
#
# Requirements: ffmpeg, running DISPLAY:1 session with Nvidia GPU

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS="$SCRIPT_DIR/walle_ws"
MEDIA_DIR="$SCRIPT_DIR/docs/media"
REAL_DISPLAY=:1
XAUTHORITY_PATH="/run/user/$(id -u)/gdm/Xauthority"
LD_FIX=/lib/x86_64-linux-gnu/libpthread.so.0

RAW_VIDEO="/tmp/walle_demo_raw.mp4"
PALETTE="/tmp/walle_palette.png"
OUTPUT_GIF="$MEDIA_DIR/demo_v4.gif"

# Demo commands to send to the robot (after model loads)
DEMO_COMMANDS=(
    "go to the orange box"
    "find the red chair"
)
# Seconds to record each command phase
RECORD_SECS_PER_CMD=45

# ── Parse args ────────────────────────────────────────────────────────────────
SIM_ALREADY_UP=false
for arg in "$@"; do
    [[ "$arg" == "--sim-already-up" ]] && SIM_ALREADY_UP=true
done

echo "============================================"
echo "  WallE3 Demo Recorder"
echo "============================================"

source /opt/ros/jazzy/setup.bash
source "$WS/install/setup.bash"

# ── Start simulation if needed ────────────────────────────────────────────────
if [ "$SIM_ALREADY_UP" = false ]; then
    echo ">>> Starting simulation (this will take ~50s to fully load)..."
    bash "$SCRIPT_DIR/run_walle.sh" > /tmp/walle_demo_run.log 2>&1 &
    RUN_PID=$!

    echo "    Waiting 50s for Gazebo + VLM model to load..."
    sleep 50
    echo "    Simulation ready."
else
    echo ">>> Using existing simulation."
fi

# ── Start screen recording ────────────────────────────────────────────────────
TOTAL_SECS=$(( ${#DEMO_COMMANDS[@]} * RECORD_SECS_PER_CMD + 10 ))
echo ">>> Recording ${TOTAL_SECS}s of DISPLAY${REAL_DISPLAY} → $RAW_VIDEO"
echo "    Resolution: 1280x480 (left half: Gazebo, right half: RViz2)"

DISPLAY=$REAL_DISPLAY \
XAUTHORITY=$XAUTHORITY_PATH \
ffmpeg -y \
    -f x11grab \
    -framerate 10 \
    -video_size 1280x480 \
    -i "${REAL_DISPLAY}+0,300" \
    -c:v libx264 \
    -preset ultrafast \
    -crf 28 \
    -t "$TOTAL_SECS" \
    "$RAW_VIDEO" \
    > /tmp/ffmpeg_record.log 2>&1 &
FFMPEG_PID=$!
echo "    ffmpeg PID=$FFMPEG_PID"

sleep 3   # let recording settle

# ── Send demo commands ────────────────────────────────────────────────────────
echo ">>> Sending demo commands to robot..."
for cmd in "${DEMO_COMMANDS[@]}"; do
    echo "    Command: \"$cmd\""
    ros2 topic pub --once /user_command std_msgs/msg/String \
        "{data: '$cmd'}" > /dev/null 2>&1 || true
    echo "    Waiting ${RECORD_SECS_PER_CMD}s for robot to execute..."
    sleep "$RECORD_SECS_PER_CMD"
done

# ── Stop recording ────────────────────────────────────────────────────────────
echo ">>> Stopping recording..."
kill "$FFMPEG_PID" 2>/dev/null || true
wait "$FFMPEG_PID" 2>/dev/null || true

if [ ! -f "$RAW_VIDEO" ]; then
    echo "ERROR: Recording failed — $RAW_VIDEO not found."
    echo "Check /tmp/ffmpeg_record.log for details."
    exit 1
fi

echo "    Raw video: $(du -h "$RAW_VIDEO" | cut -f1)"

# ── Convert to GIF ────────────────────────────────────────────────────────────
echo ">>> Converting to GIF (palette generation + dither)..."

# Step 1: generate palette for best color quality
ffmpeg -y -i "$RAW_VIDEO" \
    -vf "fps=8,scale=1280:-1:flags=lanczos,palettegen=stats_mode=diff" \
    "$PALETTE" > /dev/null 2>&1

# Step 2: apply palette with dither
ffmpeg -y \
    -i "$RAW_VIDEO" \
    -i "$PALETTE" \
    -lavfi "fps=8,scale=1280:-1:flags=lanczos [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" \
    "$OUTPUT_GIF" > /dev/null 2>&1

SIZE=$(du -h "$OUTPUT_GIF" | cut -f1)
echo ""
echo "============================================"
echo "  Done: $OUTPUT_GIF ($SIZE)"
echo ""
echo "  Next steps:"
echo "    1. Review the GIF to check quality"
echo "    2. If good: git add docs/media/demo_v4.gif && git commit && git push"
echo "    3. Update README.md: change demo_v3.gif -> demo_v4.gif"
echo "    4. Optional: rm docs/media/demo_v3.gif"
echo "============================================"

# Cleanup
rm -f "$RAW_VIDEO" "$PALETTE"
