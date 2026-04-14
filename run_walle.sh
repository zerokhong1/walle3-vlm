#!/bin/bash
# WallE3 v2 — One-command startup
# Run Gazebo directly on DISPLAY:1 (NVIDIA GPU) so camera sensor works
# Camera → VLM inference → robot navigation

set -e

REAL_DISPLAY=:1
XAUTHORITY_PATH="/run/user/$(id -u)/gdm/Xauthority"
LD_FIX=/lib/x86_64-linux-gnu/libpthread.so.0
# Derive workspace from the location of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS="$SCRIPT_DIR/walle_ws"

echo "============================================"
echo "  WallE3 v2 — VLM-Powered Autonomous Robot"
echo "============================================"
echo ""

# ── Cleanup ───────────────────────────────────────────────────────────────────
echo ">>> Cleaning up old processes..."
pkill -f "gz sim"        2>/dev/null || true
pkill -f "rviz2"         2>/dev/null || true
pkill -f "ros2 launch"   2>/dev/null || true
pkill -f "ros2 run"      2>/dev/null || true
pkill -f "wander"        2>/dev/null || true
pkill -f "expressive"    2>/dev/null || true
pkill -f "perception"    2>/dev/null || true
pkill -f "vlm_planner"   2>/dev/null || true
pkill -f "language_interface" 2>/dev/null || true
pkill -f "Xvfb :99"     2>/dev/null || true
sleep 1
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99 2>/dev/null || true

source /opt/ros/jazzy/setup.bash
source $WS/install/setup.bash

# ── 1. Gazebo simulation + AI nodes — DISPLAY:1 with NVIDIA GPU ──────────────
echo ">>> [1/3] Starting Gazebo simulation + AI nodes (NVIDIA GPU, camera enabled)..."
echo "    headless:=false  →  Gazebo GUI + camera sensor rendering active"

DISPLAY=$REAL_DISPLAY \
XAUTHORITY=$XAUTHORITY_PATH \
LD_PRELOAD=$LD_FIX \
ros2 launch walle_bringup sim.launch.py \
  headless:=false \
  start_demo:=true \
  start_perception:=false \
  start_vlm:=false \
  > /tmp/walle_server.log 2>&1 &
SIM_PID=$!
echo "    Simulation PID=$SIM_PID"

# ── Wait for Gazebo + controllers to start ───────────────────────────────────
echo "    Waiting 25s for Gazebo + controllers..."
sleep 25
grep -q "diff_drive_base_controller" /tmp/walle_server.log \
  && echo "    OK — Controllers active" \
  || echo "    WARN — Controllers may still be loading"

# ── 2. RViz2 ─────────────────────────────────────────────────────────────────
echo ">>> [2/3] Opening RViz2..."
DISPLAY=$REAL_DISPLAY \
XAUTHORITY=$XAUTHORITY_PATH \
LD_PRELOAD=$LD_FIX \
LIBGL_ALWAYS_SOFTWARE=1 \
GALLIUM_DRIVER=llvmpipe \
ros2 run rviz2 rviz2 \
  -d "$SCRIPT_DIR/walle.rviz" \
  > /tmp/rviz2.log 2>&1 &
RVIZ_PID=$!
echo "    RViz2 PID=$RVIZ_PID"

# ── 3. VLM Stack ─────────────────────────────────────────────────────────────
echo ">>> [3/3] Starting VLM stack (Qwen2.5-VL, loading model ~20s)..."
DISPLAY=$REAL_DISPLAY \
XAUTHORITY=$XAUTHORITY_PATH \
ros2 launch walle_bringup vlm.launch.py \
  use_sim_time:=true \
  start_vlm_perception:=false \
  > /tmp/vlm_stack.log 2>&1 &
VLM_PID=$!
echo "    VLM PID=$VLM_PID"

# ── Confirm windows open ─────────────────────────────────────────────────────
sleep 8
echo ""
echo "============================================"
echo "  WallE3 v2 is running!"
echo ""
echo "  Camera topics:"
echo "    /camera/image_raw      — live robot camera"
echo "    /camera/vlm_annotated  — camera + VLM overlay"
echo ""
echo "  VLM topics:"
echo "    /user_command          — send commands to robot"
echo "    /vlm/action_plan       — action plan JSON"
echo "    /behavior_state        — robot state"
echo ""
echo "  Example command:"
echo "    ros2 topic pub --once /user_command std_msgs/msg/String \\"
echo "      \"{data: 'go to the orange box'}\""
echo ""
echo "  Stop: Ctrl+C"
echo "============================================"

wait
