# Postmortem Template — WallE3 VLM

**Use for:** Safety incidents, mission abort spikes, VLM degradation events, hardware failures

---

## Incident Summary

| Field | Value |
|-------|-------|
| Incident ID | INC-[YYYY-MM-DD]-[NNN] |
| Date/Time | |
| Duration | |
| Severity | S0 / S1 / S2 / S3 |
| Affected component | vlm_planner / wander / cmd_vel_mux / hardware / sim |
| Reporter | |
| Incident commander | |

**One-line summary:** [What happened, to what, with what impact]

---

## Timeline

| Time | Event |
|------|-------|
| T+0:00 | Incident detected |
| T+X:XX | [action taken] |
| T+X:XX | [action taken] |
| T+X:XX | Incident resolved |

---

## Impact

- Missions affected: [count]
- Duration of impact: [minutes]
- Safety events triggered: [count, severity]
- Operator interventions required: [count]
- Data lost: [yes/no — rosbag available?]

---

## Root Cause Analysis

**5 Whys:**

1. Why did [symptom] occur? → Because [cause 1]
2. Why did [cause 1] occur? → Because [cause 2]
3. Why did [cause 2] occur? → Because [cause 3]
4. Why did [cause 3] occur? → Because [cause 4]
5. Why did [cause 4] occur? → Because [root cause]

**Root cause:** [One sentence]

---

## Evidence

- Rosbag: `~/walle_bags/[path]`
- Safety event CSV: `~/walle_logs/safety_events_[date].csv`
- Mission log: `~/walle_logs/missions_[date].csv`
- Related ISSUES.md entry: [I-XXX]

---

## Resolution

**Immediate fix:** [What was done to stop the incident]

**Permanent fix:** [Code change / config change / process change]

**Commit / PR:** [link]

---

## Lessons Learned

**What went well:**
-

**What didn't go well:**
-

**What would we do differently:**
-

---

## Action Items

| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
| | | | |

---

## Prevention

**How do we prevent recurrence?**

- [ ] Regression test added: [test ID]
- [ ] FMEA updated: [risk ID]
- [ ] Monitoring/alerting added: [KPI or alert]
- [ ] Documentation updated: [doc]

---

## Sign-off

| Role | Name | Date |
|------|------|------|
| Safety Officer | | |
| Engineering Lead | | |
| Product | | |
