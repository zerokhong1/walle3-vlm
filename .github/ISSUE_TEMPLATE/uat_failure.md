---
name: UAT Failure
about: Report a failed UAT test case from the UAT test plan
title: "[UAT FAIL] T-XX — "
labels: uat, bug
assignees: ''
---

## Test Case

**ID:** T-[XX]
**Name:** [from UAT test plan]
**Maps to:** FR-[XX] / US-[XX]

## Expected Result

[Copy from UAT test plan]

## Actual Result

[What happened instead]

## Failure Evidence

- [ ] Screenshot / video
- [ ] Rosbag: `~/walle_bags/[path]`
- [ ] Topic output: paste here

## Failure Classification

- [ ] Safety regression (blocks release)
- [ ] Functional failure (P1 — fix before release)
- [ ] Performance regression (P2 — acceptable with waiver)
- [ ] Environment issue (not a product bug)

## Root Cause (if known)

[File, function, line if identifiable]

## Impact on Release

- [ ] Blocks R[X] release — must fix
- [ ] Does not block — acceptable for this release with documented waiver
