from __future__ import annotations

import base64
import binascii
from io import BytesIO
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import wave

from .runtime import GenerationError


class LlamaCppSpeechRuntime:
    """TTS client for Liquid's CPU-capable llama.cpp audio runner."""

    TTS_PROMPT = "Perform TTS in japanese."

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    @property
    def loaded(self) -> bool:
        # The runner owns model lifecycle in its own process.
        return False

    def synthesize(self, text: str) -> bytes:
        request_body = {
            "model": "",
            "modalities": ["audio"],
            "messages": [
                {"role": "system", "content": self.TTS_PROMPT},
                {"role": "user", "content": text},
            ],
            "stream": True,
            "max_tokens": 512,
            "reset_context": True,
        }
        request = Request(
            f"{self.base_url}/v1/chat/completions",
            data=json.dumps(request_body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        audio = bytearray()
        sample_rate = 24_000
        try:
            with urlopen(request, timeout=300) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8").strip()
                    if not line.startswith("data: "):
                        continue
                    data = line.removeprefix("data: ")
                    if data == "[DONE]":
                        break
                    chunk = json.loads(data)
                    if error := chunk.get("error"):
                        raise GenerationError(error.get("message", "LFM audio runner failed"))
                    choices = chunk.get("choices", [])
                    if not choices:
                        continue
                    output = choices[0].get("delta", {}).get("audio")
                    if not output:
                        continue
                    sample_rate = int(output.get("sample_rate", sample_rate))
                    audio.extend(base64.b64decode(output["data"]))
        except (
            HTTPError,
            URLError,
            TimeoutError,
            json.JSONDecodeError,
            KeyError,
            ValueError,
            binascii.Error,
        ) as error:
            raise GenerationError(f"LFM audio runner に接続できません: {error}") from error

        if not audio:
            raise GenerationError("LFM audio runner から音声合成結果を取得できませんでした。")

        output = BytesIO()
        with wave.open(output, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(audio)
        return output.getvalue()
