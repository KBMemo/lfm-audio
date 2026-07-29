from __future__ import annotations

from io import BytesIO
import threading


class RuntimeErrorBase(RuntimeError):
    """An error which can be safely returned by the HTTP service."""


class AudioDecodeError(RuntimeErrorBase):
    pass


class GenerationError(RuntimeErrorBase):
    pass


class LiquidAudioRuntime:
    """Lazy, single-process LFM2.5-Audio runtime.

    The upstream model and processor are intentionally loaded on the first audio
    request. A deployment can warm the process with a synthetic request without
    making `/health` download model weights or consume model memory.
    """

    SAMPLE_RATE = 24_000
    ASR_PROMPT = "Perform ASR in japanese."
    TTS_PROMPT = "Perform TTS in japanese."

    def __init__(self, model_id: str):
        self.model_id = model_id
        self._model = None
        self._processor = None
        self._lock = threading.Lock()

    @property
    def loaded(self) -> bool:
        return self._model is not None and self._processor is not None

    def transcribe(self, audio_bytes: bytes) -> str:
        with self._lock:
            self._load()
            torch, soundfile, chat_state = self._imports()
            wav, sample_rate = self._read_audio(soundfile, audio_bytes)

            chat = chat_state(self._processor)
            chat.new_turn("system")
            chat.add_text(self.ASR_PROMPT)
            chat.end_turn()
            chat.new_turn("user")
            chat.add_audio(torch.from_numpy(wav).unsqueeze(0), sample_rate)
            chat.end_turn()
            chat.new_turn("assistant")

            tokens = []
            for token in self._model.generate_sequential(**chat, max_new_tokens=512):
                if token.numel() == 1:
                    tokens.append(token)

            text = "".join(self._processor.text.decode(token) for token in tokens).strip()
            if not text:
                raise GenerationError("音声から文字起こし結果を取得できませんでした。")
            return text

    def synthesize(self, text: str) -> bytes:
        with self._lock:
            self._load()
            torch, soundfile, chat_state = self._imports()

            chat = chat_state(self._processor)
            chat.new_turn("system")
            chat.add_text(self.TTS_PROMPT)
            chat.end_turn()
            chat.new_turn("user")
            chat.add_text(text)
            chat.end_turn()
            chat.new_turn("assistant")

            audio_tokens = []
            for token in self._model.generate_sequential(
                **chat, max_new_tokens=512, audio_temperature=0.8, audio_top_k=64
            ):
                if token.numel() > 1:
                    audio_tokens.append(token)

            if len(audio_tokens) < 2:
                raise GenerationError("音声合成結果を取得できませんでした。")

            waveform = self._processor.decode(torch.stack(audio_tokens[:-1], 1).unsqueeze(0))
            output = BytesIO()
            soundfile.write(output, waveform.cpu()[0].numpy(), self.SAMPLE_RATE, format="WAV")
            return output.getvalue()

    def _load(self) -> None:
        if self.loaded:
            return

        try:
            from liquid_audio import LFM2AudioModel, LFM2AudioProcessor
        except ImportError as error:
            raise GenerationError("liquid-audio がインストールされていません。") from error

        self._processor = LFM2AudioProcessor.from_pretrained(self.model_id).eval()
        self._model = LFM2AudioModel.from_pretrained(self.model_id).eval()

    @staticmethod
    def _imports():
        try:
            import soundfile
            import torch
            from liquid_audio import ChatState
        except ImportError as error:
            raise GenerationError("LFM audio runtime の依存関係を読み込めません。") from error
        return torch, soundfile, ChatState

    @staticmethod
    def _read_audio(soundfile, audio_bytes: bytes):
        try:
            wav, sample_rate = soundfile.read(BytesIO(audio_bytes), dtype="float32", always_2d=True)
        except RuntimeError as error:
            raise AudioDecodeError("対応していない、または壊れた音声ファイルです。") from error

        if wav.size == 0:
            raise AudioDecodeError("音声ファイルが空です。")

        # The model accepts a single waveform. Downmix multi-channel recordings.
        return wav.mean(axis=1), sample_rate
