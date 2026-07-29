#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
runner_dir="$repo_root/vendor/llama-liquid-audio"
model_dir="$repo_root/models/LFM2.5-Audio-1.5B-JP-GGUF"
base_url="https://huggingface.co/LiquidAI/LFM2.5-Audio-1.5B-JP-GGUF/resolve/main"

mkdir -p "$runner_dir" "$model_dir"

curl --fail --location --continue-at - \
  --output "$runner_dir/runner.zip" \
  "$base_url/runners/llama-liquid-audio-ubuntu-x64.zip"
unzip -oq "$runner_dir/runner.zip" -d "$runner_dir"

for file in \
  LFM2.5-Audio-1.5B-JP-Q4_0.gguf \
  mmproj-LFM2.5-Audio-1.5B-JP-Q4_0.gguf \
  vocoder-LFM2.5-Audio-1.5B-JP-Q4_0.gguf \
  tokenizer-LFM2.5-Audio-1.5B-JP-Q4_0.gguf; do
  curl --fail --location --continue-at - --output "$model_dir/$file" "$base_url/$file"
done
