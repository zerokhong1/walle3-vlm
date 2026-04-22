# ADR-004 — Local VLM inference (Qwen2.5-VL-3B INT4) over cloud API

**Status:** Accepted
**Date:** Jan 2026
**Deciders:** Cong Thai
**Related:** PDL-004, BR-006, NFR-002

---

## Context

The robot needs vision-language model (VLM) capability to interpret camera frames and generate navigation plans. Two categories of solution exist: (1) cloud APIs (GPT-4V, Gemini, Claude Vision), and (2) locally-hosted open models.

Hardware constraint: NVIDIA RTX 3060 12 GB. Gazebo Harmonic uses approximately 6.7 GB VRAM, leaving ~5.3 GB for the VLM model.

---

## Decision

Use Qwen2.5-VL-3B-Instruct with INT4 quantization (BitsAndBytes) running locally on the robot's GPU.

- **Model size at runtime:** ~2 GB VRAM (INT4, 3B parameters)
- **Inference latency:** 8–12s per frame on RTX 3060 (p50 ~9s, p95 ~11s in sample data)
- **Accepted by:** NFR-002 (≤10s p50 target; p50 = 9.2s in sample runs)
- **Compatible with dual-loop architecture:** inference runs in background thread; fast loop continues at 50Hz

---

## Alternatives considered

| Alternative | Reason rejected |
|-------------|----------------|
| GPT-4V / Gemini Vision (cloud API) | Violates BR-006 (no cloud dependency: operator data must stay on-premise; no subscription cost; no API latency). |
| Qwen2.5-VL 7B (local) | Requires ~8 GB VRAM; exceeds budget with Gazebo running (~6.7 GB already used). |
| Qwen2.5-VL 72B (local) | Requires multi-GPU or high-end server GPU. Far outside hardware budget. |
| LLaVA or other open VLM | Qwen2.5-VL-3B outperforms comparable-size LLaVA on spatial reasoning and Vietnamese language tasks. |
| Ollama + API wrapper | Ollama adds an HTTP server layer, increasing inter-process latency. Direct Transformers call is simpler and faster. |
| YOLOv8 object detection only | Object detection alone cannot interpret spatial relationships or respond to natural language goal descriptions. Planned as confidence fallback (not primary inference). |

---

## Consequences

**Positive:**
- No cloud cost, no API rate limits, no privacy exposure (telemetry stays on-premise).
- Inference latency is predictable (not dependent on internet or cloud load).
- Satisfies BR-006 (affordable — no ongoing API subscription).
- Supports Vietnamese language natively (not all cloud APIs do).

**Negative:**
- 8–12s inference latency requires dual-loop architecture (ADR-001). Navigation quality is limited by inference frequency (~6 frames/minute).
- INT4 quantization degrades accuracy slightly vs FP16/BF16 (acceptable tradeoff at 3B scale).
- If GPU is unavailable (laptop, no NVIDIA), model fails to load — simulation falls back to no-VLM mode.
- Confidence threshold not enforced in R0 (tracked as I-010) — model may produce low-confidence plans.

---

## Future reconsideration triggers

- If a deployment site offers GPU-as-a-service on local network: consider 7B model with higher accuracy.
- If latency < 3s is required: consider distilled edge VLM or dedicated inference board (Jetson AGX Orin).
- If multi-language support is required beyond EN+VI: re-evaluate model.
- YOLOv8 fallback (FR-009, `fallback_to_yolo=false` in config): implemented as a future option, currently disabled.

---

## Implementation

- Model loading: `vlm_utils.py` — `AutoModelForVision2Seq` with `BitsAndBytesConfig(load_in_4bit=True)`
- Model: `Qwen/Qwen2.5-VL-3B-Instruct` from HuggingFace Hub
- Config: `vlm_config.yaml` — `model_id`, `inference_interval`, `max_new_tokens`
- Validated by: UAT T-19 (SKIP in simulation — requires GPU); sample `fact_inference_events.csv` shows p50=9.2s, p95=10.4s
