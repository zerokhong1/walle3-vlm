# ADR-003 — std_msgs/String + JSON for all telemetry events

**Status:** Accepted
**Date:** Feb 2026
**Deciders:** Cong Thai
**Related:** PDL-006, FR-017, FR-018, NFR-013

---

## Context

WallE3 produces telemetry from multiple nodes (vlm_planner, wander, stuck_watchdog). Module B (`walle3-mission-analytics`) needs to ingest and query this telemetry. The question is how to structure the message types for cross-module communication.

Two competing concerns:
1. **Type safety:** Custom `.msg` files enforce field types at compile time.
2. **Loose coupling:** Module B should be able to evolve independently of Module A. Adding a field to a message should not require recompiling Module B.

---

## Decision

Use `std_msgs/String` with JSON payloads for all telemetry topics. Schema version is embedded in the `/mission/started` payload as `schema_version: "1.0"`.

All 7 event topics use this pattern:
- `/mission/started` — `{mission_id, mission_type, user_command, timestamp, robot_id, site_id, schema_version}`
- `/mission/completed` — `{mission_id, success, duration_s, intervention_count, reason}`
- `/safety/event` — `{event_type, severity, timestamp}`
- `/inference/event` — `{model, latency_ms, input_tokens, output_valid, target_found, confidence}`
- `/planner/state`, `/controller/mode`, `/mux/active_channel` — plain strings (enum-like, no JSON needed)

---

## Alternatives considered

| Alternative | Reason rejected |
|-------------|----------------|
| Custom `.msg` types (e.g., `MissionCompleted.msg`) | Requires shared dependency between Module A and Module B packages. Adding a field requires recompiling both. Violates module isolation (NFR-014). |
| Protobuf / FlatBuffers | Overkill for simulation MVP. Adds toolchain complexity (proto compiler, generated Python bindings). |
| ROS 2 action / service | Actions are for request-response workflows, not one-way telemetry. Services require synchronous response. |
| MQTT / external message broker | Adds infrastructure dependency. Increases deployment complexity. Out of scope for R0. |

---

## Consequences

**Positive:**
- Module A and Module B can evolve independently — adding a field to JSON does not break existing consumers.
- Any JSON consumer (Python, Node.js, SQL, Power BI) can ingest without ROS dependency.
- Schema version in payload enables forward compatibility detection.
- `mission_logger_node.py` can write directly to CSV by parsing JSON — no custom message deserialization needed.

**Negative:**
- No compile-time type checking — field name typos cause silent failures at runtime.
- JSON parsing overhead (negligible at telemetry frequencies, but not zero).
- Schema enforcement requires runtime validation logic (not implemented in R0 — tracked as future work).

---

## Implementation

- All telemetry publishers: `std_msgs.msg.String` with `json.dumps(payload)`
- Schema documentation: `docs/product/09_event_contract_v1.md`
- Consumer: `mission_logger_node.py` — subscribes to all topics, parses JSON, writes CSV rows
- Schema versioning: `schema_version` field in `/mission/started` payload
- Validated by: UAT T-06 (telemetry logging confirmed), analytics sample data schema consistency
