#!/bin/bash
# WallE3 v2 — One-command startup
# Run Gazebo directly on DISPLAY:1 (NVIDIA GPU) so camera sensor works
# Camera → VLM inference → robot navigation
#
# Usage:
#   bash run_walle.sh                  # arena world (default)
#   bash run_walle.sh --world warehouse  # VinMotion warehouse world

set -e

REAL_DISPLAY=:1
XAUTHORITY_PATH="/run/user/$(id -u)/gdm/Xauthority"
LD_FIX=/lib/x86_64-linux-gnu/libpthread.so.0
# Derive workspace from the location of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS="$SCRIPT_DIR/walle_ws"

# ── Parse arguments ────────────────────────────────────────────────────────────
WORLD="arena"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --world)
            WORLD="$2"
            shift 2
            ;;
        --world=*)
            WORLD="${1#*=}"
            shift
            ;;
        *)
            echo "Unknown argument: $1"
            echo "Usage: bash run_walle.sh [--world arena|warehouse]"
            exit 1
            ;;
    esac
done

# ── Select launch file + spawn position based on world ────────────────────────
case "$WORLD" in
    warehouse)
        LAUNCH_FILE="sim_warehouse.launch.py"
        SPAWN_ARGS="x:=1.0 y:=7.5 z:=0.25"
        WORLD_DESC="VinMotion Warehouse (20×15m)"
        ;;
    arena|*)
        LAUNCH_FILE="sim.launch.py"
        SPAWN_ARGS="x:=0.0 y:=0.0 z:=0.25"
        WORLD_DESC="Arena (8×8m)"
        WORLD="arena"
        ;;
esac

echo "============================================"
echo "  WallE3 v2 — VLM-Powered Autonomous Robot"
echo "  World: $WORLD_DESC"
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
pkill -f "mission_logger" 2>/dev/null || true
pkill -f "Xvfb :99"     2>/dev/null || true
sleep 1
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99 2>/dev/null || true

source /opt/ros/jazzy/setup.bash
source $WS/install/setup.bash

# ── 1. Gazebo simulation + AI nodes — DISPLAY:1 with NVIDIA GPU ──────────────
echo ">>> [1/4] Starting Gazebo simulation ($WORLD_DESC, NVIDIA GPU)..."
echo "    headless:=false  →  Gazebo GUI + camera sensor rendering active"

DISPLAY=$REAL_DISPLAY \
XAUTHORITY=$XAUTHORITY_PATH \
LD_PRELOAD=$LD_FIX \
ros2 launch walle_bringup $LAUNCH_FILE \
  headless:=false \
  start_demo:=true \
  start_perception:=false \
  start_vlm:=false \
  $SPAWN_ARGS \
  > /tmp/walle_server.log 2>&1 &
SIM_PID=$!
echo "    Simulation PID=$SIM_PID  (launch: $LAUNCH_FILE)"

# ── Wait for Gazebo + controllers to start ───────────────────────────────────
echo "    Waiting 25s for Gazebo + controllers..."
sleep 25
grep -q "diff_drive_base_controller" /tmp/walle_server.log \
  && echo "    OK — Controllers active" \
  || echo "    WARN — Controllers may still be loading"

# ── 2. RViz2 ─────────────────────────────────────────────────────────────────
echo ">>> [2/4] Opening RViz2..."
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
echo ">>> [3/4] Starting VLM stack (Qwen2.5-VL, loading model ~20s)..."
DISPLAY=$REAL_DISPLAY \
XAUTHORITY=$XAUTHORITY_PATH \
ros2 launch walle_bringup vlm.launch.py \
  use_sim_time:=true \
  start_vlm_perception:=false \
  > /tmp/vlm_stack.log 2>&1 &
VLM_PID=$!
echo "    VLM PID=$VLM_PID"

# ── 4. Mission Logger ─────────────────────────────────────────────────────────
echo ">>> [4/4] Starting mission logger (CSV → ~/walle_logs/)..."
ros2 run walle_demo mission_logger \
  --ros-args \
  -p log_dir:="$HOME/walle_logs" \
  -p robot_id:=walle3 \
  -p site_id:=$WORLD \
  > /tmp/mission_logger.log 2>&1 &
LOGGER_PID=$!
echo "    Logger PID=$LOGGER_PID"

# ── Confirm windows open ─────────────────────────────────────────────────────
sleep 8
echo ""
echo "============================================"
echo "  WallE3 v2 is running!  [$WORLD_DESC]"
echo ""
echo "  Camera topics:"
echo "    /camera/image_raw      — live robot camera"
echo "    /camera/vlm_annotated  — camera + VLM overlay"
echo ""
echo "  VLM topics:"
echo "    /user_command          — send commands to robot"
echo "    /vlm/action_plan       — action plan JSON"
echo "    /planner/state         — mission lifecycle (IDLE|PLANNING|SEARCHING|APPROACHING|CONFIRMING|COMPLETED)"
echo "    /controller/mode       — controller mode (VLM_TASK|CAM_AVOID|LIDAR_AVOID|WANDER|EMERGENCY_STOP)"
echo ""
echo "  Telemetry:"
echo "    /mission/started       — mission start event (JSON)"
echo "    /mission/completed     — mission end event (JSON)"
echo "    /mux/active_channel    — active cmd_vel channel (SAFETY|VLM|WANDER)"
echo "    /safety/event          — collision, stuck events"
echo "    ~/walle_logs/          — CSV fact tables (mission_logger)"
echo "    ~/walle_bags/          — auto-recorded rosbags on safety events"
echo ""
echo "  Example commands:"
echo "    ros2 topic pub --once /user_command std_msgs/msg/String \\"
echo "      \"{data: 'go to the orange box'}\""
if [[ "$WORLD" == "warehouse" ]]; then
echo ""
echo "  Warehouse targets:"
echo "    'go to the carton box in Zone B'"
echo "    'find the pallet in Zone A'"
echo "    'navigate to the picking area'"
fi
echo ""
echo "  Stop: Ctrl+C"
echo "============================================"

wait
