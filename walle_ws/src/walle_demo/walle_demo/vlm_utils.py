#!/usr/bin/env python3
"""VLM utilities — model loading, prompt templates, JSON parsing.

Supports two backends:
  - "transformers"  : HuggingFace (local GPU, default)
  - "ollama"        : Ollama server (if ollama serve is running)
"""

from __future__ import annotations

import base64
import json
import re
import time
from typing import Any, Dict, Optional

import cv2
import numpy as np

# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT_VI = """Bạn là bộ não AI của robot WALL-E di động.
Robot có:
- Camera phía trước (bạn đang thấy ảnh từ camera này)
- LiDAR 360° (hệ thống an toàn tự động, bạn không cần lo)
- Differential drive: tiến/lùi/quay trái/phải
- Đầu 2-DOF: xoay yaw ±0.65 rad, pitch ±0.5 rad
- 2 cánh tay: giơ lên/xuống ±1.0 rad

Quy tắc phản hồi:
1. Luôn trả lời bằng JSON hợp lệ — không giải thích thêm
2. Nếu không thấy target → action.type = "search"
3. Nếu target bên trái → turn_left, head_yaw > 0
4. Nếu target bên phải → turn_right, head_yaw < 0
5. Khi target ở center và gần → stop
6. Tốc độ max linear = 0.25 m/s, angular max = 0.8 rad/s
7. Mô tả scene bằng tiếng Việt ngắn gọn"""

SYSTEM_PROMPT_EN = """You are the AI brain of a mobile WALL-E robot.
The robot has:
- A front-facing camera (you see images from this camera)
- LiDAR safety layer (handled automatically — ignore it)
- Differential drive: go_forward / turn_left / turn_right / stop / search
- 2-DOF head: yaw ±0.65 rad, pitch ±0.5 rad
- 2 arms: raise/lower ±1.0 rad

Rules:
1. Always reply with valid JSON only — no extra text or explanation
2. If target not visible → action.type = "search", turn slowly to look around
3. Target on left → turn_left (angular > 0)
4. Target on right → turn_right (angular < 0)
5. Target centered and close (near) → stop, status = "reached"
6. Target centered but far/medium → go_forward, status = "approaching"
7. Max linear speed = 0.25 m/s, max angular = 0.6 rad/s
8. scene: describe briefly in English what you see"""

ACTION_PROMPT_TEMPLATE = """{system}

Task: {command}

Look at the camera image and reply with JSON only:
{{
  "scene": "<brief description of what you see>",
  "target_found": true/false,
  "target_position": "left/center/right/unknown",
  "target_distance": "near/medium/far/unknown",
  "action": {{
    "type": "go_forward/turn_left/turn_right/stop/search",
    "speed": 0.0,
    "angular": 0.0,
    "head_yaw": 0.0,
    "head_pitch": 0.0,
    "arm_left": 0.0,
    "arm_right": 0.0,
    "duration_sec": 1.0
  }},
  "status": "searching/approaching/reached/not_found",
  "message": "<short status message>"
}}
Reply with JSON only, no explanation."""

SCENE_PROMPT = """Briefly describe what you see in the robot camera image.
Reply with JSON only:
{
  "scene": "<description in 1-2 sentences>",
  "objects": ["<object 1>", "<object 2>", ...],
  "obstacles": "<describe obstacles ahead, or 'none'>",
  "lighting": "bright/normal/dark"
}
Reply with JSON only."""


# ── JSON extraction ───────────────────────────────────────────────────────────

def extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Extract first valid JSON object from model output."""
    # Try direct parse first
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find JSON block between ```json ... ``` or { ... }
    for pattern in [r'```json\s*([\s\S]+?)\s*```', r'(\{[\s\S]+\})']:
        m = re.search(pattern, text)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
    return None


def make_default_plan(command: str = "", status: str = "searching") -> Dict[str, Any]:
    """Return a safe default plan when VLM fails or times out."""
    return {
        "scene": "Scene unknown",
        "target_found": False,
        "target_position": "unknown",
        "target_distance": "unknown",
        "action": {
            "type": "search",
            "speed": 0.0,
            "angular": 0.3,
            "head_yaw": 0.0,
            "head_pitch": 0.0,
            "arm_left": 0.0,
            "arm_right": 0.0,
            "duration_sec": 1.0,
        },
        "status": status,
        "message": f"Searching for: {command}",
    }


# ── Image encoding ────────────────────────────────────────────────────────────

def frame_to_base64(frame: np.ndarray, quality: int = 85) -> str:
    """Encode OpenCV BGR frame to base64 JPEG string."""
    _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return base64.b64encode(buf.tobytes()).decode('utf-8')


def frame_to_pil(frame: np.ndarray):
    """Convert OpenCV BGR frame to PIL Image."""
    from PIL import Image as PILImage
    return PILImage.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))


# ── Backend: Transformers ─────────────────────────────────────────────────────

class TransformersBackend:
    """Local HuggingFace Transformers backend for Qwen2.5-VL."""

    def __init__(self, model_name: str = "Qwen/Qwen2.5-VL-7B-Instruct",
                 quantize_4bit: bool = True, logger=None) -> None:
        self.model_name = model_name
        self.quantize_4bit = quantize_4bit
        self.log = logger
        self.model = None
        self.processor = None
        self.ready = False

    def load(self) -> bool:
        try:
            import torch
            from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration, BitsAndBytesConfig

            if self.log:
                self.log(f"Loading {self.model_name} (4bit={self.quantize_4bit}) ...")

            bnb_config = None
            if self.quantize_4bit:
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4",
                )

            self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                self.model_name,
                quantization_config=bnb_config,
                device_map="auto",
                torch_dtype=torch.float16 if not self.quantize_4bit else None,
            )
            self.processor = AutoProcessor.from_pretrained(
                self.model_name,
                min_pixels=64 * 28 * 28,
                max_pixels=128 * 28 * 28,
            )
            self.ready = True
            if self.log:
                self.log("Qwen2.5-VL model loaded and ready.")
            return True
        except Exception as e:
            if self.log:
                self.log(f"Failed to load model: {e}")
            return False

    def infer(self, frame: np.ndarray, prompt: str,
              system: str = SYSTEM_PROMPT_VI, max_new_tokens: int = 256) -> str:
        """Run VLM inference. Returns raw text output."""
        if not self.ready:
            return ""

        import torch
        from qwen_vl_utils import process_vision_info

        pil_img = frame_to_pil(frame)

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": [
                {"type": "image", "image": pil_img},
                {"type": "text", "text": prompt},
            ]},
        ]

        text_input = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = self.processor(
            text=[text_input],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        ).to(self.model.device)

        with torch.no_grad():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                temperature=None,
                top_p=None,
            )
        # Strip prompt tokens
        generated = output_ids[:, inputs['input_ids'].shape[1]:]
        return self.processor.batch_decode(
            generated, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )[0]


# ── Backend: Ollama ───────────────────────────────────────────────────────────

class OllamaBackend:
    """Ollama server backend (requires `ollama serve` running)."""

    def __init__(self, model_name: str = "qwen2.5vl:7b",
                 host: str = "http://localhost:11434", logger=None) -> None:
        self.model_name = model_name
        self.host = host
        self.log = logger
        self.ready = False

    def load(self) -> bool:
        try:
            import ollama
            client = ollama.Client(host=self.host)
            client.list()  # ping
            self.client = client
            self.ready = True
            if self.log:
                self.log(f"Ollama backend ready: {self.host} model={self.model_name}")
            return True
        except Exception as e:
            if self.log:
                self.log(f"Ollama not available: {e}")
            return False

    def infer(self, frame: np.ndarray, prompt: str,
              system: str = SYSTEM_PROMPT_VI, max_new_tokens: int = 512) -> str:
        if not self.ready:
            return ""
        b64 = frame_to_base64(frame)
        response = self.client.chat(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt, "images": [b64]},
            ],
            options={"num_predict": max_new_tokens, "temperature": 0.1},
        )
        return response["message"]["content"]


# ── Unified VLM interface ─────────────────────────────────────────────────────

class VLMInterface:
    """Unified wrapper — tries Ollama first, falls back to Transformers."""

    def __init__(self, config: Dict[str, Any], logger=None) -> None:
        self.log = logger
        self.backend: Any = None
        self.ready = False
        self.language = config.get("language", "vi")
        self.system_prompt = SYSTEM_PROMPT_VI if self.language == "vi" else SYSTEM_PROMPT_EN

        backend_name = config.get("model_backend", "transformers")

        if backend_name == "ollama":
            b = OllamaBackend(
                model_name=config.get("model_name", "qwen2.5vl:7b"),
                host=config.get("api_endpoint", "http://localhost:11434"),
                logger=logger,
            )
            if b.load():
                self.backend = b
                self.ready = True
                return
            # Fall through to transformers
            if self.log:
                self.log("Ollama unavailable — falling back to Transformers.")

        # Transformers (default)
        model_id = config.get("model_name", "Qwen/Qwen2.5-VL-7B-Instruct")
        if ":" in model_id:          # ollama-style "qwen2.5vl:7b" → remap
            model_id = "Qwen/Qwen2.5-VL-7B-Instruct"
        b = TransformersBackend(
            model_name=model_id,
            quantize_4bit=config.get("quantize_4bit", True),
            logger=logger,
        )
        if b.load():
            self.backend = b
            self.ready = True

    def plan(self, frame: np.ndarray, command: str,
             timeout_sec: float = 10.0) -> Dict[str, Any]:
        """Generate an action plan from image + command. Returns parsed dict."""
        if not self.ready or self.backend is None:
            return make_default_plan(command, "not_found")

        # ACTION_PROMPT_TEMPLATE no longer embeds {system} — system is passed
        # separately to the model's system role (not duplicated in user message)
        prompt = ACTION_PROMPT_TEMPLATE.format(system='', command=command).lstrip()
        try:
            t0 = time.monotonic()
            raw = self.backend.infer(frame, prompt, system=self.system_prompt)
            elapsed = time.monotonic() - t0
            if self.log:
                self.log(f"[VLM] inference {elapsed:.2f}s → {raw[:80]!r}")
            parsed = extract_json(raw)
            if parsed:
                return parsed
        except Exception as e:
            if self.log:
                self.log(f"[VLM] inference error: {e}")
        return make_default_plan(command)

    def describe_scene(self, frame: np.ndarray) -> Dict[str, Any]:
        """Return a scene description dict."""
        if not self.ready or self.backend is None:
            return {"scene": "VLM not ready", "objects": [], "obstacles": "unknown"}
        try:
            raw = self.backend.infer(frame, SCENE_PROMPT, system=self.system_prompt,
                                     max_new_tokens=256)
            parsed = extract_json(raw)
            if parsed:
                return parsed
        except Exception as e:
            if self.log:
                self.log(f"[VLM scene] error: {e}")
        return {"scene": "Không xác định", "objects": [], "obstacles": "unknown"}
