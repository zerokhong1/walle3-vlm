# ADR-001 — Dual-loop VLM architecture (50Hz safety + background inference)

**Status:** Accepted
**Date:** Feb 2026
**Deciders:** Cong Thai
**Related:** PDL-001, NFR-001, NFR-002

---

## Context

Qwen2.5-VL-3B-Instruct inference takes 8–12 seconds on an RTX 3060 12 GB (INT4). A synchronous architecture would block all robot behavior for 8–12 seconds per inference cycle, during which the robot cannot respond to obstacles, operator commands, or stuck conditions.

The robot must simultaneously satisfy two conflicting requirements:

- **NFR-001:** Fast-loop frequency ≥ 50 Hz (real-time safety response)
- **NFR-002:** VLM inference latency ≤ 10s p50 (intelligence / navigation quality)

These two requirements have incompatible time constants: 20ms vs 10,000ms.

---

## Decision

Run two independent loops:

1. **Fast loop (50 Hz ROS timer):** Reads the last available plan (protected by `plan_lock`), executes LiDAR safety checks, and publishes `/cmd_vel/vlm` or `/cmd_vel/safety`. Always runs, regardless of inference state.

2. **Background inference thread (daemon thread):** Captures camera frame, runs Qwen2.5-VL inference, writes new plan to `self._plan` under `plan_lock`. Produces approximately 1 plan every 5–15s depending on GPU load.

The fast loop consumes the last valid plan until a new one arrives. Stop keywords (`stop`, `halt`, etc.) are intercepted in `_command_cb` before any VLM call — guaranteed < 20ms halt.

---

## Alternatives considered

| Alternative | Reason rejected |
|-------------|----------------|
| Synchronous VLM (inference in ROS timer callback) | Robot blocks for 8–12s per cycle. Cannot avoid obstacles during inference. Unsafe. |
| Reduce VLM model size | Smaller models still take 2–4s for 3B; accuracy degrades. Does not solve the blocking problem. |
| Cloud VLM API (GPT-4V, Gemini) | Violates BR-006 (no cloud dependency). Latency unpredictable. Privacy risk. |
| Separate VLM microservice over network | Adds network dependency, latency jitter, and deployment complexity. Dual-loop is simpler and achieves same decoupling. |

---

## Consequences

**Positive:**
- Fast loop runs at ≥ 40Hz even under full GPU load (simulation constraint; target 50Hz on hardware).
- Stop commands are handled in < 5ms regardless of inference state (T-01 PASS, max 4.6ms).
- Safety layer is independent of AI capability — if VLM fails, wander/avoidance still runs.

**Negative:**
- Requires thread-safe shared state (`plan_lock`, `scan_lock`, `frame_lock`).
- Plan becomes stale between inference cycles (15s stale plan limit: NFR-008).
- Debugging is harder — race conditions are possible if lock discipline is broken.
- Camera frame captured at start of inference may be 8–12s old when plan executes.

---

## Implementation

- Fast loop: `vlm_planner.py:235` — `self.fast_timer = self.create_timer(0.02, self._fast_loop)`
- Inference thread: `vlm_planner.py` — `threading.Thread(target=self._inference_loop, daemon=True)`
- Plan lock: `self._plan_lock = threading.Lock()`
- Stop fast-path: `vlm_planner.py:285` — checked in `_command_cb` before VLM branch
