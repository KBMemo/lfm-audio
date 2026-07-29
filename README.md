# LFM Audio Service

Private ASR and TTS service backed by `LiquidAI/LFM2.5-Audio-1.5B-JP`.
It exposes a minimal OpenAI-compatible audio API for Nyoy and KBMemo; it is not
a public endpoint and is not managed by llama-switchd.

## API

All audio endpoints require `Authorization: Bearer $LFM_AUDIO_TOKEN`.

```text
GET  /health
POST /v1/audio/transcriptions
POST /v1/audio/speech
```

`/v1/audio/transcriptions` accepts a Japanese WebM, Ogg, WAV, or MP4 recording
as multipart `file`, plus `model=LiquidAI/LFM2.5-Audio-1.5B-JP`. It returns
`{"text":"..."}`. `/v1/audio/speech` accepts JSON and returns `audio/wav`.

## Local setup

```sh
python3 -m venv .venv
.venv/bin/python -m ensurepip --upgrade
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
cp env.example .env
set -a; . ./.env; set +a
.venv/bin/lfm-audio-service
```

The first transcription or synthesis loads model weights. Run a warmup request
before evaluating latency. Keep the service bound to loopback or a private
network and set a non-empty service token.

## Smoke checks

```sh
curl -fsS http://127.0.0.1:10120/health

curl -fsS -X POST http://127.0.0.1:10120/v1/audio/transcriptions \
  -H "Authorization: Bearer $LFM_AUDIO_TOKEN" \
  -F "file=@sample.wav;type=audio/wav" \
  -F 'model=LiquidAI/LFM2.5-Audio-1.5B-JP' \
  -F language=ja

curl -fsS -X POST http://127.0.0.1:10120/v1/audio/speech \
  -H "Authorization: Bearer $LFM_AUDIO_TOKEN" \
  -H 'Content-Type: application/json' \
  --data '{"model":"LiquidAI/LFM2.5-Audio-1.5B-JP","input":"音声合成の確認です。","voice":"default","response_format":"wav"}' \
  --output sample.wav
```

## Deployment

Install `systemd/lfm-audio.service` as a user service after copying the project
to `~/services/lfm-audio`, creating `.venv`, and adding a private
`.env.production`. The service deliberately has no deploy hook in Nyoy or
KBMemo: model runtime lifecycle is independent from Rails deploys.
