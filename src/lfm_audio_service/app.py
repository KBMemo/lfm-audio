from __future__ import annotations

from hmac import compare_digest

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel, Field

from .config import Settings
from .runner import LlamaCppSpeechRuntime
from .runtime import AudioDecodeError, GenerationError, LiquidAudioRuntime


ALLOWED_AUDIO_TYPES = {"audio/webm", "audio/ogg", "audio/wav", "audio/x-wav", "audio/mp4"}


class SpeechRequest(BaseModel):
    model: str
    input: str = Field(min_length=1)
    voice: str = "default"
    response_format: str = "wav"


def create_app(settings: Settings | None = None, runtime: LiquidAudioRuntime | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    runtime = runtime or LiquidAudioRuntime(settings.model, device=settings.device)
    speech_runtime = _speech_runtime(settings, runtime)
    app = FastAPI(title="LFM Audio Service", version="0.1.0")

    def require_token(authorization: str | None = Header(default=None)) -> None:
        expected = settings.token
        actual = authorization.removeprefix("Bearer ").strip() if authorization else ""
        if not expected or not compare_digest(actual, expected):
            raise HTTPException(status_code=401, detail="unauthorized")

    def require_model(model: str) -> None:
        if model != settings.model:
            raise HTTPException(status_code=422, detail="configured model must be used")

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "model": settings.model,
            "device": settings.device,
            "loaded": runtime.loaded,
            "capabilities": {"transcription": True, "speech": speech_runtime is not None},
            "tts_backend": settings.tts_backend,
        }

    @app.post("/v1/audio/transcriptions", dependencies=[Depends(require_token)])
    async def transcriptions(
        file: UploadFile = File(...),
        model: str = Form(...),
        language: str = Form("ja"),
        prompt: str | None = Form(default=None),
    ):
        del prompt
        require_model(model)
        if language not in {"ja", "japanese"}:
            raise HTTPException(status_code=422, detail="only Japanese transcription is supported")
        if file.content_type not in ALLOWED_AUDIO_TYPES:
            raise HTTPException(status_code=422, detail="unsupported audio content type")

        payload = await file.read(settings.max_upload_bytes + 1)
        if len(payload) > settings.max_upload_bytes:
            raise HTTPException(status_code=413, detail="audio file is too large")

        try:
            text = await run_in_threadpool(runtime.transcribe, payload)
        except AudioDecodeError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except GenerationError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        return {"text": text}

    @app.post("/v1/audio/speech", dependencies=[Depends(require_token)])
    async def speech(request: SpeechRequest):
        require_model(request.model)
        if request.voice != "default":
            raise HTTPException(status_code=422, detail="only the default Japanese voice is supported")
        if request.response_format != "wav":
            raise HTTPException(status_code=422, detail="only wav output is supported")
        if len(request.input) > settings.max_input_chars:
            raise HTTPException(status_code=413, detail="speech input is too long")

        try:
            if speech_runtime is None:
                raise GenerationError("音声合成 backend が設定されていません。")
            audio = await run_in_threadpool(speech_runtime.synthesize, request.input)
        except GenerationError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        return Response(content=audio, media_type="audio/wav")

    return app


def _speech_runtime(settings: Settings, runtime: LiquidAudioRuntime):
    if settings.tts_backend == "llama_cpp":
        return LlamaCppSpeechRuntime(settings.runner_url)
    if settings.tts_backend == "python":
        return runtime
    return None
