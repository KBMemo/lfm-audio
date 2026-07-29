# LFM Audio Service

Private ASR and TTS service backed by `LiquidAI/LFM2.5-Audio-1.5B-JP`.
It exposes a minimal OpenAI-compatible audio API for Nyoy and KBMemo; it is not
a public endpoint and is not managed by llama-switchd.

On a CPU-only host, the upstream Python `liquid-audio` runtime supports ASR but
not TTS: its LFM2.5 audio detokenizer requires CUDA. For CPU TTS, enable the
official LFM2.5-Audio-JP GGUF runner. The facade keeps the same audio API and
forwards synthesis to the runner's private OpenAI-compatible endpoint.

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
scripts/install_cpu.sh
cp env.example .env
set -a; . ./.env; set +a
.venv/bin/lfm-audio-service
```

The first transcription or synthesis loads model weights. Run a warmup request
before evaluating latency. Keep the service bound to loopback or a private
network and set a non-empty service token. On CPU-only hosts, set
`LFM_AUDIO_CPU_THREADS` to the number of usable CPU cores.

## CPU TTS with GGUF

The official Japanese GGUF release includes a dedicated
`llama-liquid-audio-server` binary. Install its Q4 model components and runner:

```sh
scripts/install_gguf_runner.sh
cp systemd/lfm-audio-runner.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now lfm-audio-runner
```

Set these values in `.env.production`, then restart `lfm-audio`:

```sh
LFM_AUDIO_TTS_BACKEND=llama_cpp
LFM_AUDIO_RUNNER_URL=http://127.0.0.1:10121
```

`lfm-audio-runner` is loopback-only and intentionally unauthenticated. Only the
facade is the authenticated service boundary. The runner accepts one request at
a time, so callers should treat TTS as a queued operation.

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
`.env.production`. For CPU TTS, install `systemd/lfm-audio-runner.service`
first. These services deliberately have no deploy hook in Nyoy or KBMemo:
model runtime lifecycle is independent from Rails deploys.
