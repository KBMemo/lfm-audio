from __future__ import annotations

import base64
from io import BytesIO
import json
import unittest
from unittest.mock import patch
import wave

from lfm_audio_service.runner import LlamaCppSpeechRuntime


class FakeResponse:
    def __init__(self, lines: list[bytes]):
        self.lines = lines

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def __iter__(self):
        return iter(self.lines)


class LlamaCppSpeechRuntimeTest(unittest.TestCase):
    def test_synthesize_converts_streamed_pcm_to_wav(self):
        pcm = b"\x00\x00\x10\x00"
        chunk = {
            "choices": [
                {"delta": {"audio": {"data": base64.b64encode(pcm).decode(), "sample_rate": 24_000}}}
            ]
        }
        response = FakeResponse([f"data: {json.dumps(chunk)}\n".encode(), b"data: [DONE]\n"])

        with patch("lfm_audio_service.runner.urlopen", return_value=response) as urlopen:
            output = LlamaCppSpeechRuntime("http://runner.local").synthesize("テストです")

        with wave.open(BytesIO(output)) as wav:
            self.assertEqual(1, wav.getnchannels())
            self.assertEqual(24_000, wav.getframerate())
            self.assertEqual(pcm, wav.readframes(2))

        request = urlopen.call_args.args[0]
        self.assertEqual("http://runner.local/v1/chat/completions", request.full_url)
