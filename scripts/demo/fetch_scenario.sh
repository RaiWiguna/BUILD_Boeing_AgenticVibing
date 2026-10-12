#!/usr/bin/env bash
# Prepare the demo scenario assets under data/demo-scenarios/ (ignored by Git).
# Requires: SSH access to the research VM (key path in SSH_KEY), ffmpeg, python3, and the
# cached STT research output at outputs/tartan-research/transcripts50.json (88) and
# outputs/tartan-research/stt-87/run.json (87).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DIR="$ROOT/data/demo-scenarios/kagc-2022-09-10-88"
SSH_KEY="${SSH_KEY:?Set SSH_KEY to the research VM deploy key path}"
VM="${VM:?Set VM to the research VM login (user@host)}"
REMOTE="/home/deploy/flowlens-research/tartan/kagc-plus30-05/09-10-22_audio/88.wav"
EXPECTED="8c114b9f37e8ef0ca35735e4aea89634db1ec9040a397cdc3d679ce981fde7a3"
EXPECTED_87="34f189130e908974a9d7be9f196b2a4d7c768a8ae54413f114ff35d100d3df4f"

mkdir -p "$DIR/derived"
if [ ! -f "$DIR/88.wav" ]; then
  scp -o BatchMode=yes -o IdentitiesOnly=yes -i "$SSH_KEY" "$VM:$REMOTE" "$DIR/88.wav"
fi
actual="$(shasum -a 256 "$DIR/88.wav" | cut -d' ' -f1)"
[ "$actual" = "$EXPECTED" ] || { echo "88.wav checksum mismatch" >&2; exit 1; }

# 87.wav (recorded before 88.wav) comes from the public TartanAviation archive.
if [ ! -f "$DIR/87.wav" ]; then
  tmp="$(mktemp -d)"
  python3 -I "$ROOT/outputs/tartan-research/tools/tartan_sample.py" --key kagc/2022/9/09-10-22_audio.zip \
    --output "$tmp" --members 09-10-22_audio/87.wav --max-files 1 --max-transfer-mib 45 --max-member-mib 100
  cp "$(find "$tmp" -name 87.wav | head -1)" "$DIR/87.wav"
  rm -rf "$tmp"
fi
actual="$(shasum -a 256 "$DIR/87.wav" | cut -d' ' -f1)"
[ "$actual" = "$EXPECTED_87" ] || { echo "87.wav checksum mismatch" >&2; exit 1; }
[ -f "$ROOT/outputs/tartan-research/stt-87/run.json" ] || { echo "missing STT cache for 87.wav" >&2; exit 1; }

python3 "$ROOT/scripts/demo/synth_adsb.py"
python3 "$ROOT/scripts/demo/build_scenario.py"
echo "Scenario ready: $DIR"
