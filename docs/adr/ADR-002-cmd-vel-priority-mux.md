# ADR-002 — Priority cmd_vel mux for velocity arbitration

**Status:** Accepted
**Date:** Mar 2026
**Deciders:** Cong Thai
**Related:** PDL-002, FR-015, I-006

---

## Context

Three nodes publish velocity commands: `vlm_planner`, `wander`, and safety handlers inside both nodes. Before this decision, all three wrote directly to `/diff_drive_base_controller/cmd_vel`. Last-writer-wins at the ROS network level, which means:

- `vlm_planner` publishes at 50 Hz overwriting `wander`'s LIDAR_AVOID escape commands.
- No observable record of which node is "winning" at any given time.
- Robot appeared stuck because it was receiving conflicting commands at 50Hz.

---

## Decision

Implement a dedicated 3-channel mux node (`cmd_vel_mux.py`) with fixed priority:

| Priority | Channel | Topic | Timeout | Use case |
|----------|---------|-------|---------|----------|
| 0 (highest) | SAFETY | `/cmd_vel/safety` | 250ms | Emergency stops, LiDAR escapes, operator halt |
| 1 | VLM | `/cmd_vel/vlm` | 150ms | VLM navigation plan execution |
| 2 (lowest) | WANDER | `/cmd_vel/wander` | 250ms | Wandering, reactive avoidance in idle |

The mux runs at 50 Hz and forwards the highest-priority channel that has a non-expired message. Expiry is time-based (not signal-based) — if a node crashes, its channel silently times out and the next priority wins.

---

## Alternatives considered

| Alternative | Reason rejected |
|-------------|----------------|
| Single publisher (wander arbitrates internally) | Creates tight coupling — wander must know about VLM state. Violates separation of concerns. |
| `twist_mux` ROS package | Not tested with `TwistStamped` in ROS 2 Jazzy at time of decision; adds external dependency; less control over timeout behavior. |
| VLM planner arbitrates internally | VLM planner would need to subscribe to wander outputs and re-publish. Increases complexity and single point of failure. |
| Hardware relay (physical signal) | Over-engineering for a simulation MVP; applicable only when PLd+ safety is required. |

---

## Consequences

**Positive:**
- Safety channel always wins — mechanically enforced by mux logic.
- `/mux/active_channel` provides observable evidence of which node is commanding the robot at any time.
- Node crash = silent timeout → graceful degradation to next priority.
- Channels are independently testable (inject on `/cmd_vel/safety` directly to verify priority).

**Negative:**
- Safety channel timeout (250ms) means a brief gap after the last safety command before lower priority takes over. This is intentional but must be tuned.
- Adding a third node in the control path increases latency by approximately 1–2 mux cycles (≤ 40ms at 50 Hz).
- Mux node failure = no cmd_vel forwarded. Mitigated by watchdog monitoring.

---

## Implementation

- Mux node: `cmd_vel_mux.py`
- Priority table: `_CHANNELS = [('/cmd_vel/safety', 'SAFETY', 0.25), ('/cmd_vel/vlm', 'VLM', 0.15), ('/cmd_vel/wander', 'WANDER', 0.25)]`
- Mux loop timer: `self.create_timer(1.0 / 50.0, self._mux_loop)`
- Observable output: `/mux/active_channel` (String)
- Validated by: UAT T-06 (PASS — safety won 27/31 output commands)
