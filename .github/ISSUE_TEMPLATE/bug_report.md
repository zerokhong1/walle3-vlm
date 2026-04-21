---
name: Bug Report
about: Report a bug in robot behavior, safety, or telemetry
title: "[BUG] "
labels: bug
assignees: ''
---

## Severity

- [ ] S0 — Critical (safety regression, data loss, crash)
- [ ] S1 — High (significant behavior degradation)
- [ ] S2 — Medium (incorrect behavior with workaround)
- [ ] S3 — Low (cosmetic, minor)

## Summary

[One sentence: what went wrong, where, with what impact]

## Symptom

Describe what you observed. Include:
- What the robot did
- What state/mode it was in (`ros2 topic echo /planner/state`)
- What you expected to happen

## Steps to Reproduce

1.
2.
3.

## Environment

- World: arena / warehouse
- Run command:
- Commit:
- ROS 2 version:
- GPU:

## Evidence

- [ ] Rosbag available: `~/walle_bags/[path]`
- [ ] Safety event log: `~/walle_logs/safety_events_[date].csv`
- [ ] Terminal output / screenshot

## Root Cause Hypothesis

[Optional — your best guess at root cause]

## Proposed Fix

[Optional]
