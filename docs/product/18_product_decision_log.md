# Product Decision Log — WallE3 VLM

**Format:** Decision | Context | Alternatives | Rationale | Date

---

## PDL-001 — Dual-loop architecture (50Hz safety + background VLM)

**Decision:** Run safety + navigation at 50Hz in a ROS timer, VLM inference in a background daemon thread.

**Context:** Qwen2.5-VL 3B takes 8–12s per inference on RTX 3060. A synchronous architecture would block the robot for 12s between decisions.

**Alternatives considered:**
- A: Synchronous — simple but robot freezes during inference (rejected: unsafe)
- B: Reduce VLM model size — less accurate, still blocks (rejected: doesn't solve problem)
- C: Dual-loop — chosen

**Rationale:** Robot must remain reactive to obstacles at all times, even during inference. The 50Hz fast loop handles safety; background thread handles intelligence. This is the only architecture that satisfies both NFR-001 (≥50Hz) and NFR-002 (VLM runs).

**Date:** Feb 2026

---

## PDL-002 — Priority mux: 3 channels, timeout-based

**Decision:** Implement cmd_vel_mux with 3 channels (safety P0 > vlm P1 > wander P2) using time-based expiry (not signal-based preemption).

**Context:** vlm_planner and wander both needed to publish velocity commands without racing.

**Alternatives:**
- A: Single publisher (wander arbitrates) — creates tight coupling between wander and VLM (rejected)
- B: twist_mux package — not tested with TwistStamped in ROS 2 Jazzy; adds dependency (rejected)
- C: Custom 3-channel mux — chosen

**Rationale:** Separate topics prevent race conditions. Timeout-based expiry naturally handles node crashes (silent timeout → lower priority wins). Clean separation of concerns.

**Date:** Mar 2026

---

## PDL-003 — Stop keyword fast-path (bypass VLM)

**Decision:** Detect stop keywords in `_command_cb` before any VLM call. Publish safety channel halt immediately.

**Context:** BR-004 requires < 20ms stop latency. VLM inference takes 8–12s.

**Alternatives:**
- A: Stop command queued to VLM — latency 8–12s (rejected: fails BR-004)
- B: Dedicated stop topic — more complex topic graph (rejected: unnecessary)
- C: Fast-path in command callback — chosen

**Rationale:** Simplest path that achieves < 20ms. No additional topics. Stop keywords are a fixed set, no AI needed.

**Date:** Mar 2026

---

## PDL-004 — VLM model: Qwen2.5-VL 3B INT4 over larger models

**Decision:** Use Qwen2.5-VL 3B with INT4 quantization (BitsAndBytes) instead of larger 7B or 72B models.

**Context:** Hardware constraint: RTX 3060 12 GB. Gazebo uses ~6.7 GB VRAM leaving ~5.3 GB for VLM.

**Alternatives:**
- A: Qwen2.5-VL 7B — requires ~8 GB VRAM (exceeds available VRAM with Gazebo running)
- B: Cloud API (GPT-4V, Gemini) — cloud dependency violates BR-006; latency unpredictable
- C: Qwen2.5-VL 3B INT4 (~2 GB VRAM) — chosen

**Rationale:** 3B INT4 fits in budget VRAM with Gazebo. 8–12s latency acceptable given dual-loop architecture. Local inference satisfies no-cloud requirement (BR-006).

**Date:** Jan 2026

---

## PDL-005 — LiDAR: extend from 180° to 360° (I-016)

**Decision:** Change LiDAR URDF config from min_angle=-π/2, max_angle=π/2 (180°) to min_angle=-π, max_angle=π (360°).

**Context:** I-016 diagnostic revealed robot hitting walls without triggering safety. Root cause: LiDAR only covered frontal 180°; reverse escape maneuvers had zero rear coverage.

**Alternatives:**
- A: Keep 180°, add rear proximity sensor — additional hardware cost and integration (rejected)
- B: Extend to 360° — config change only, no hardware cost (chosen)
- C: Add physical bumper only — doesn't fix proactive avoidance (rejected as standalone)

**Rationale:** 360° LiDAR is the correct behavior for a mobile robot. The original 180° config was a configuration error, not a design choice. Zero hardware cost. Fix deployed in ddaba81.

**Date:** Apr 2026

---

## PDL-006 — Event contract: std_msgs/String with JSON over custom message types

**Decision:** Use `std_msgs/String` with JSON payloads for all telemetry events, not custom `.msg` files.

**Context:** Module B needs to ingest telemetry. Custom message types require cross-package dependencies.

**Alternatives:**
- A: Custom .msg types — type-safe but requires shared dependency between A and B (rejected: tight coupling)
- B: std_msgs/String + JSON — loose coupling, schema versioned in payload (chosen)

**Rationale:** Module A and B can evolve independently. Schema version in `/mission/started` payload handles compatibility. Any JSON consumer (Python, Node.js, SQL) can ingest without ROS dependency.

**Date:** Feb 2026

---

## PDL-007 — wander.py: add LiDAR safety check during VLM_TASK (I-016 BUG-3)

**Decision:** During VLM_TASK mode, wander.py runs a secondary LiDAR check (threshold = 55% of safe_dist) and publishes via safety channel if triggered.

**Context:** BUG-3 in I-016: wander returned early during VLM_TASK without any LiDAR check, leaving only vlm_planner's safety (which had BUG-2: narrow sector).

**Alternatives:**
- A: No wander safety during VLM_TASK — relies entirely on vlm_planner (rejected: single point of failure)
- B: Full wander logic during VLM_TASK — would interfere with VLM navigation at normal distances (rejected)
- C: Tight-threshold secondary check — only triggers on emergency proximity (chosen)

**Rationale:** Defense-in-depth. Two independent safety checks using same physical LiDAR but different code paths. Tight threshold (36cm) prevents false positives during normal VLM navigation.

**Date:** Apr 2026
