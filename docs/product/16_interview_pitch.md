# Interview Pitch — WallE3 VLM

**Version:** 1.0 | **Date:** April 2026

---

## 30-Second Pitch

WallE3 là robot dịch vụ dùng Vision-Language Model để nhận lệnh tự nhiên như "đi tới thùng màu cam" và điều hướng tới mục tiêu mà không cần lập trình waypoint. Tôi productize project này thành một case study BA/PM bằng cách viết BRD, PRD, backlog, KPI framework, UAT test plan, risk register và roadmap từ MVP kỹ thuật đến pilot readiness.

Điểm tôi muốn thể hiện là khả năng biến một prototype robotics thành một MVP có yêu cầu, metric, safety governance và kế hoạch pilot rõ ràng.

---

## 60-Second Pitch (English)

WallE3 VLM is an autonomous service robot that understands natural language commands — "go to the orange box", "find the red chair" — using a locally-running Vision-Language Model. No waypoint programming. No cloud dependency.

I built this as both a robotics engineering project and a BA/PM case study. On the engineering side: ROS 2 Jazzy, Qwen2.5-VL running on a $400 GPU, real-time safety loop at 50Hz. On the product side: I wrote a BRD with 8 business requirements, a PRD with 23 functional requirements, a 4-sprint backlog with 14 user stories, a KPI framework tied directly to telemetry events, a FMEA-lite with 12 failure modes, and a 24-scenario UAT plan.

The most interesting product challenge was when I discovered the robot was hitting walls without any LiDAR trigger. I ran a structured 6-phase diagnostic — data flow, data quality, logic, priority arbitration — identified 3 root causes across 3 files, fixed them in 3 separate commits, and documented the root cause analysis in the risk register. That's the kind of systematic thinking I bring to product problems.

---

## 2-Minute Pitch (Detailed)

### Opening hook
"Tell me about a project where you had to turn technical complexity into a product requirement."

---

WallE3 started as a pure robotics engineering question: can a 3-billion-parameter vision-language model run on a $400 GPU and understand natural language navigation commands well enough to be useful?

The answer turned out to be yes — but getting from "yes technically" to "yes as a product" required a completely different skill set.

**The problem I was solving for:**
Warehouse operators in Vietnam spend 15–30% of their time on locate-and-fetch tasks. Existing robot solutions require expensive waypoint reprogramming after every layout change. I defined this as the core problem and wrote a Business Requirements Document with 8 requirements, the most important being: "a warehouse operator with zero robotics training can issue 5 distinct navigation commands within 10 minutes of first use."

**How I structured the product:**
I built a priority-arbitrated safety architecture — think of it like a product decision: which behavior wins when two systems conflict? I defined the product rule: safety always beats navigation, which always beats wandering. That became a functional requirement in the PRD, a test case in the UAT plan, and a risk mitigation in the FMEA.

**The moment that changed everything:**
In week 3, I discovered the robot was driving into walls without triggering any safety alarm. It looked like the system was working — state machine showed APPROACHING, telemetry was publishing — but physically, the robot would hit the wall.

I ran a structured diagnostic: 6 phases, static code analysis across 5 files. I found 3 root causes:
1. The LiDAR was only scanning 180° (frontal half) — rear was completely blind
2. The VLM planner was only checking a 17° frontal sector — a wall at 20° off dead-ahead was invisible
3. The safety layer was completely bypassed when VLM was active

I fixed each in a separate commit, documented the root cause in the risk register as R-002 (RPN=48), and wrote a regression test T-03 in the UAT plan.

**What this showed me:**
Safety is not an engineering concern — it's a product requirement with measurable acceptance criteria, a place in the FMEA, and a regression test that blocks every future release. That mindset shift is what I bring to BA/PM work.

**Current status:**
R0 (technical MVP) is complete in simulation. R1 (productized MVP with full documentation) is what you're looking at. Next milestone is finding a pilot partner for a warehouse or mall deployment.

---

## Interview Question Bank

### "Walk me through a trade-off you made"

**The dual-loop architecture:**
VLM inference takes 8–12 seconds. A naive implementation would block the robot for 12 seconds between decisions — which means it can't avoid obstacles during inference. I specified a dual-loop architecture: a 50Hz safety loop runs independently while a background thread handles VLM inference. The trade-off was added complexity (thread safety, lock management) for a system that stays reactive during inference. I documented this as NFR-001 (≥50Hz fast loop) and NFR-002 (≤10s VLM latency) — two requirements with different owners and different failure modes.

---

### "How did you handle scope?"

I used MoSCoW on a 4-sprint backlog. Sprint 1 was entirely safety stories — nothing else shipped until the robot could stop reliably. That's a product principle: the robot must stop before it can navigate. Three features I explicitly put in the "Won't Have" category for R0: autonomous charging, WMS integration, fleet coordination. Each time someone suggested adding them, I pointed to the roadmap: "that's R4, here's why."

---

### "What did you learn from this project?"

Three things:
1. Safety is a product requirement, not an engineering concern. It belongs in the PRD with measurable acceptance criteria.
2. Telemetry schema is a product decision. The event contract I designed forced me to define "mission success" precisely before writing any test.
3. Structured diagnostics are more valuable than fast fixes. Finding 3 root causes with a 6-phase approach took 2 hours. A guess-and-check approach would have taken days and might have missed BUG-3 (the wander safety bypass).

---

## CV Bullets

**Long version:**
> Productized a ROS 2 + Qwen2.5-VL autonomous robot prototype into a BA/PM-ready robotics MVP by defining BRD (8 business requirements), PRD (23 functional + 9 non-functional requirements), user journey maps, 28-story backlog with acceptance criteria, KPI dashboard spec (8 metrics), event contract v1.0, FMEA-lite risk register (12 failure modes), 24-scenario UAT plan, and 4-release roadmap (R0–R4). Root-caused and fixed an S0 wall-collision regression (I-016) via structured 6-phase diagnostic.

**Short version:**
> Built full BA/PM documentation for an autonomous robotics MVP: BRD, PRD, backlog, KPI framework, safety FMEA, UAT plan, and release roadmap from simulation MVP to pilot readiness.

**LinkedIn headline:**
> Robotics + BA/PM | WallE3 VLM | ROS 2 · Vision-Language Models · Product Requirements · Safety FMEA | VinUniversity
