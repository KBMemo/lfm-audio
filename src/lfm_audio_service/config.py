from __future__ import annotations

from dataclasses import dataclass
import os


DEFAULT_MODEL = "LiquidAI/LFM2.5-Audio-1.5B-JP"


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    token: str
    model: str
    max_upload_bytes: int
    max_input_chars: int
    cpu_threads: int

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            host=os.environ.get("LFM_AUDIO_HOST", "127.0.0.1"),
            port=int(os.environ.get("LFM_AUDIO_PORT", "10120")),
            token=os.environ.get("LFM_AUDIO_TOKEN", "").strip(),
            model=os.environ.get("LFM_AUDIO_MODEL", DEFAULT_MODEL).strip(),
            max_upload_bytes=int(os.environ.get("LFM_AUDIO_MAX_UPLOAD_BYTES", str(10 * 1024 * 1024))),
            max_input_chars=int(os.environ.get("LFM_AUDIO_MAX_INPUT_CHARS", "4000")),
            cpu_threads=int(os.environ.get("LFM_AUDIO_CPU_THREADS", "0")),
        )
