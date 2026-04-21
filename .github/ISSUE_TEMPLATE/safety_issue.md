---
name: Safety Issue
about: Report a safety concern — robot collision, unexpected motion, or unsafe behavior
title: "[SAFETY] "
labels: safety, priority-s0
assignees: ''
---

> **STOP:** If this is an active safety incident in a physical deployment, halt the robot immediately (hardware e-stop), preserve all logs, then file this report.

## Incident Type

- [ ] Robot contacted person
- [ ] Robot contacted property (damage)
- [ ] Robot contacted property (near-miss)
- [ ] Robot did not stop on stop command
- [ ] LiDAR/camera safety not triggered when expected
- [ ] State machine reported safe state during unsafe event
- [ ] Other:

## Severity

- [ ] CRITICAL — person contact or imminent risk
- [ ] HIGH — property contact or clear safety regression
- [ ] MEDIUM — potential safety issue, no contact

## What Happened

[Describe in detail: robot position, command issued, expected behavior, observed behavior]

## Timeline

| Time | Event |
|------|-------|
| | |

## Evidence

- [ ] Rosbag: `~/walle_bags/[path]`
- [ ] Safety event CSV: `~/walle_logs/safety_events_[date].csv`
- [ ] Video/screenshot
- [ ] `/safety/event` output: paste here

## Affected Requirements

- [ ] FR-010 LiDAR detection
- [ ] FR-011 Escape maneuver
- [ ] FR-012 Rear obstacle
- [ ] FR-015 Priority mux
- [ ] FR-016 Contact sensor
- [ ] Other:

## Immediate Mitigation Applied

[What was done to stop the incident]

## Root Cause Hypothesis

[If known]
