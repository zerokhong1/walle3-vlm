# Pilot Rollout Plan — WallE3 VLM

**Version:** 1.0 | **Date:** April 2026 | **Target:** R3 (Q4 2026)

---

## Pilot Objectives

1. Validate mission success rate ≥ 70% in real warehouse environment
2. Confirm zero safety incidents (person contact, property damage)
3. Collect operator NPS ≥ +30 after pilot week
4. Identify sim-to-real gaps for R4 roadmap

---

## Pilot Site Requirements

| Requirement | Specification |
|-------------|--------------|
| Floor area | ≥ 20m × 15m (matches warehouse world) |
| Lighting | ≥ 300 lux (adequate for camera) |
| Floor material | Non-reflective (avoid LiDAR floor reflection R-010) |
| Network | LAN access for workstation + ROS topics |
| Dedicated zone | Operator-only area during pilot hours (safety perimeter) |
| Power | 220V near deployment zone for GPU workstation |

---

## 90-Day Rollout Timeline

### Week 1–2: Site Survey & Hardware Prep
- [ ] Site survey: floor plan, lighting, obstacle map, power points
- [ ] Hardware assembly: robot chassis + GPU workstation
- [ ] Physical LiDAR calibration: verify 360° coverage, adjust height if < 0.25m
- [ ] Camera exposure calibration for site lighting conditions
- [ ] Safety officer walkthrough + approval form signed

### Week 3–4: Sim-to-Real Validation
- [ ] Deploy sim-identical launch on physical hardware
- [ ] Run 20 controlled trials (target: objects placed same as sim)
- [ ] Log all failures; file bug reports for sim-to-real gaps
- [ ] Tune LiDAR range filter for floor material
- [ ] Tune camera obstacle detection thresholds for site floor color

### Week 5–6: Operator Training
- [ ] Training session: command vocabulary (30 Vietnamese commands)
- [ ] Safety briefing: what to do if robot misbehaves
- [ ] Supervised practice: each operator completes 5 missions with supervisor present
- [ ] TUI training: reading state, event log, sending commands

### Week 7–8: Monitored Pilot
- [ ] Operators use robot for real tasks (supervised by Chị Lan)
- [ ] Cong Thai on-call for technical issues
- [ ] KPI dashboard live: mission success rate, intervention count, stuck rate
- [ ] Daily debrief with Chị Lan: issues, observations, suggestions

### Week 9–10: Evaluation & Handoff
- [ ] Operator NPS survey
- [ ] KPI report: all 8 metrics vs. targets
- [ ] Safety audit: review all safety events with Anh Khoa
- [ ] Failure analysis: root cause for every mission abort
- [ ] Go/No-Go decision for R4 (production readiness)

---

## Go / No-Go Criteria

| Criterion | Go | No-Go |
|-----------|----|-------|
| Mission success rate | ≥ 70% | < 60% (requires 2-week fix sprint) |
| Safety incidents (person contact) | 0 | Any → immediate pause |
| Operator NPS | ≥ +30 | < +10 → UX redesign required |
| Stuck abort rate | ≤ 20% | > 30% → navigation fix required |
| Hardware reliability (uptime) | ≥ 90% in pilot week | < 80% → hardware investigation |

---

## Rollback Plan

If any critical safety incident occurs:
1. Immediately halt robot operation (hardware e-stop)
2. Notify safety officer within 1 hour
3. Preserve rosbag + log evidence
4. Do not resume until root cause identified and mitigated
5. Safety officer re-approval required before resuming

---

## Hardware Checklist

- [ ] E-stop button mounted and tested (hardware cutoff, not software)
- [ ] Cable management: no trailing cables in robot path
- [ ] GPU workstation secured (not in robot path)
- [ ] LiDAR cover removed; sensor unobstructed
- [ ] Wheel odometry calibrated (0.1% error on 5m straight line)
- [ ] Camera focus adjusted for indoor lighting
- [ ] Battery or UPS for workstation (avoid mid-mission power cut)
- [ ] Contact sensor functional: test via direct touch before pilot
