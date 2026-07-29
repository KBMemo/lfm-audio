#!/usr/bin/env bash
set -euo pipefail

# liquid-audio permits a broad torch version range. Resolve CPU wheels first so
# pip does not install CUDA runtime packages on CPU-only hosts.
python_bin="${PYTHON_BIN:-.venv/bin/python}"

"$python_bin" -m pip install --upgrade pip
"$python_bin" -m pip install --index-url https://download.pytorch.org/whl/cpu \
  'torch==2.8.0+cpu' 'torchaudio==2.8.0+cpu'
"$python_bin" -m pip install \
  'fastapi>=0.115,<1' \
  'numpy>=1.26,<3' \
  'python-multipart>=0.0.9,<1' \
  'soundfile>=0.12,<1' \
  'uvicorn[standard]>=0.30,<1' \
  'accelerate>=1.10.1' \
  'datasets>=4.8.4' \
  'einops>=0.8.1' \
  'librosa>=0.11.0' \
  'sentencepiece>=0.2.1' \
  'transformers>=4.55.4'
"$python_bin" -m pip install --no-deps 'liquid-audio>=1.2,<2'
"$python_bin" -m pip install --no-deps -e .
