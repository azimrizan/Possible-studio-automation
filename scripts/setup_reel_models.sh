#!/usr/bin/env bash
# One-time install of the free models used by AI Video Edit (Basic mode) and AI Design. Safe to re-run.
#   bash scripts/setup_reel_models.sh            # English + multilingual speech, person cut-out
#   bash scripts/setup_reel_models.sh en         # English speech only (smaller)
# Installs into data/models (or $REEL_MODELS_DIR). Every download is pinned and checked against its SHA-256.
#
# Licences (check before commercial use and credit as required):
#   Parakeet TDT 0.6B v2 (NVIDIA)      CC-BY-4.0   https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2
#   Omnilingual ASR 1B CTC (Meta)      Apache-2.0  https://github.com/facebookresearch/omnilingual-asr
#   U^2-Net human segmentation         Apache-2.0  https://github.com/xuebinqin/U-2-Net
#   IS-Net (DIS) general segmentation  Apache-2.0  https://github.com/xuebinqin/DIS
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIR="${REEL_MODELS_DIR:-$ROOT/data/models}"
DL="$DIR/dl"
WHICH="${1:-all}"
mkdir -p "$DL" "$DIR/seg"

ASR=https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models
PARAKEET=sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8
OMNI=sherpa-onnx-omnilingual-asr-1600-languages-1B-ctc-int8-2025-11-12
SHA_PARAKEET=157c157bc51155e03e37d2466522a3a737dd9c72bb25f36eb18912964161e1ad
SHA_OMNI=27c270dfe9bc1abb35fef62c396b373577ffc55a272cb039d08487c27b0ecfaa
SHA_SEG=01eb6a29a5c4d8edb30b56adad9bb3a2a0535338e480724a213e0acfd2d1c73c
SHA_PRODUCT=60920e99c45464f2ba57bee2ad08c919a52bbf852739e96947fbb4358c0d964a  # IS-Net general use: product cut-outs (AI Design)

sha() { if command -v sha256sum >/dev/null; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi; }

fetch() {  # url file expected-sha
  local url=$1 file=$2 want=$3
  if [ -f "$file" ] && [ "$(sha "$file")" = "$want" ]; then return 0; fi
  echo "[models] downloading $(basename "$file")"
  curl -fL --retry 3 -o "$file.part" "$url"
  local got; got=$(sha "$file.part")
  if [ "$got" != "$want" ]; then
    rm -f "$file.part"
    echo "[models] checksum mismatch for $(basename "$file") (got $got). Not installing it." >&2
    exit 1
  fi
  mv "$file.part" "$file"
}

unpack() {  # archive extracted-name target-dir
  local archive=$1 name=$2 target=$3
  [ -f "$target/tokens.txt" ] && return 0
  echo "[models] unpacking $(basename "$archive")"
  tar xjf "$archive" -C "$DIR"
  rm -rf "$target"
  mv "$DIR/$name" "$target"
}

fetch "$ASR/$PARAKEET.tar.bz2" "$DL/parakeet.tar.bz2" "$SHA_PARAKEET"
unpack "$DL/parakeet.tar.bz2" "$PARAKEET" "$DIR/parakeet"

if [ "$WHICH" != "en" ]; then
  fetch "$ASR/$OMNI.tar.bz2" "$DL/omni.tar.bz2" "$SHA_OMNI"
  unpack "$DL/omni.tar.bz2" "$OMNI" "$DIR/omni"
fi

fetch "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net_human_seg.onnx" "$DIR/seg/u2net_human_seg.onnx" "$SHA_SEG"
fetch "https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-general-use.onnx" "$DIR/seg/isnet-general-use.onnx" "$SHA_PRODUCT"

echo "[models] ready in $DIR:"
ls "$DIR"
echo "[models] You can delete $DL to free space (the archives are only needed to re-install)."
