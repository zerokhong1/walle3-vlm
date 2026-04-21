# Stakeholder Communication Plan — WallE3 VLM

**Version:** 1.0 | **Date:** April 2026

---

## Stakeholder Matrix

| Stakeholder | Role | Influence | Interest | Engagement Strategy |
|-------------|------|-----------|----------|-------------------|
| Warehouse Manager | Sponsor | High | High | Weekly status; demo at milestone |
| Operators (floor) | Primary users | Low | High | Training session; feedback survey after pilot week |
| Safety Officer | Veto | High | Medium | Safety review at each release gate; incident reports |
| IT Engineer | Implementation | Medium | High | Technical handoff doc; daily async during integration |
| Finance | Budget | High | Low | ROI one-pager at R1; budget review at R3 |
| VinRobotics Stakeholder | Technical advisor | Medium | Medium | Monthly demo; R0 technical review |

---

## Communication Cadence

| Audience | Channel | Frequency | Content |
|----------|---------|-----------|---------|
| Warehouse Manager | Email + slide | Weekly | Mission success rate, key events, next milestone |
| Operators | In-person | Per phase | Training, command vocabulary, safety procedures |
| Safety Officer | Written report | Per release | Risk register update, safety event summary, sign-off request |
| IT Engineer | Slack/Zalo | Daily (async) | Blockers, integration issues, deployment status |
| Finance | One-pager | At R1, R3 | ROI projection, hardware cost, pilot outcomes |
| All stakeholders | Demo session | At each release | Live demo + Q&A |

---

## Key Messages by Stakeholder

**Warehouse Manager:**
> "WallE3 reduces fetch task time by eliminating waypoint reprogramming. Mission success rate target: 85%. ROI payback: 6 months."

**Safety Officer:**
> "Every safety event is logged with timestamp, severity, and a 60-second rosbag. The robot stops before it can cause harm — hardware-verified."

**Operators:**
> "You type what you need in Vietnamese. The robot goes. If anything looks wrong, type 'dừng' and it stops immediately."

**IT Engineer:**
> "Standard ROS 2 topics. CSV telemetry in ~/walle_logs/. Rosbags in ~/walle_bags/. No proprietary stack, no custom APIs."

---

## Escalation Path

| Severity | Issue Type | First Contact | Escalation (48h no response) |
|----------|-----------|---------------|------------------------------|
| S0 | Safety incident | Safety Officer | Warehouse Manager |
| S1 | Mission success < 70% | IT Engineer | Warehouse Manager |
| S2 | Hardware failure | IT Engineer | Vendor support |
| S3 | Feature request | Product (Cong Thai) | Backlog review |

---

## Stakeholder Sign-off Requirements

| Gate | Required Sign-offs |
|------|-------------------|
| R2 pilot approval | Warehouse Manager + Safety Officer |
| R3 physical deployment | Safety Officer + IT Engineer + Finance |
| R4 production | All stakeholders |
