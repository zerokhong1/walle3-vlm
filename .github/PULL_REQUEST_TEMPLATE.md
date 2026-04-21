# Pull Request

## Summary

[1–3 sentences: what changed and why]

## Type

- [ ] Bug fix (non-breaking)
- [ ] Safety fix — **requires safety review before merge**
- [ ] Feature (new functionality)
- [ ] Performance improvement
- [ ] Documentation
- [ ] Refactoring (no behavior change)
- [ ] Configuration change

## Related Issues

Closes: #
Maps to: FR-[XX] / NFR-[XX] / BR-[XX]

## Changes

- [ ] `vlm_planner.py` — [what changed]
- [ ] `wander.py` — [what changed]
- [ ] `cmd_vel_mux.py` — [what changed]
- [ ] URDF / SDF — [what changed]
- [ ] Launch files — [what changed]
- [ ] Documentation — [what changed]

## Safety Checklist

*Complete for any change touching: vlm_planner, wander, cmd_vel_mux, URDF, controllers.yaml*

- [ ] LiDAR safety logic unchanged or explicitly improved
- [ ] cmd_vel priority order unchanged (safety P0 > vlm P1 > wander P2)
- [ ] Stop keyword fast-path not degraded
- [ ] No new blocking call in main ROS thread (fast loop stays at 50Hz)
- [ ] Safety tests T-01 to T-06 still pass
- [ ] Regression test T-24 (I-016) still passes

## Test Evidence

- [ ] UAT test cases run: T-[XX], T-[XX]
- [ ] All pass: yes / no (if no: explain)
- [ ] Rosbag available for safety-relevant changes: yes / no

## Telemetry Impact

- [ ] No change to event contract (schema stable)
- [ ] Event contract change — schema_version incremented to [X.X]
- [ ] New topic added: [topic name, schema in 09_event_contract_v1.md]

## Documentation Updated

- [ ] ISSUES.md (if fixing an issue)
- [ ] PRD (if changing a requirement)
- [ ] Risk register (if mitigating a risk)
- [ ] Decision log (if making a product decision)
- [ ] README (if changing user-visible behavior)
