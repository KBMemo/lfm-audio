from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from lfm_audio_service.runtime import AudioDecodeError, LiquidAudioRuntime


class LiquidAudioRuntimeTest(unittest.TestCase):
    def test_normalize_asr_audio_converts_to_mono_wav(self):
        result = subprocess.CompletedProcess(args=[], returncode=0, stdout=b"wav", stderr=b"")

        with patch("lfm_audio_service.runtime.subprocess.run", return_value=result) as run:
            audio = LiquidAudioRuntime._normalize_asr_audio(b"webm")

        self.assertEqual(b"wav", audio)
        command = run.call_args.args[0]
        self.assertIn("ffmpeg", command)
        self.assertEqual("1", command[command.index("-ac") + 1])
        self.assertEqual("16000", command[command.index("-ar") + 1])
        self.assertEqual("wav", command[command.index("-f") + 1])

    def test_normalize_asr_audio_rejects_failed_conversion(self):
        result = subprocess.CompletedProcess(args=[], returncode=1, stdout=b"", stderr=b"invalid")

        with patch("lfm_audio_service.runtime.subprocess.run", return_value=result):
            with self.assertRaises(AudioDecodeError):
                LiquidAudioRuntime._normalize_asr_audio(b"invalid")

    def test_normalize_asr_audio_handles_missing_ffmpeg(self):
        with patch("lfm_audio_service.runtime.subprocess.run", side_effect=FileNotFoundError):
            with self.assertRaises(AudioDecodeError):
                LiquidAudioRuntime._normalize_asr_audio(b"webm")
