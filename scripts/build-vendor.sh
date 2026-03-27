#!/usr/bin/env bash
# build-vendor.sh — Rebuild vendor.js for the chat UI
#
# Bundles preact, htm, marked, and DOMPurify into a single IIFE that
# exposes globals (window.preact, window.preactHooks, window.html,
# window.marked, window.DOMPurify).
#
# Prerequisites: Node.js >= 18
#
# Usage:
#   bash scripts/build-vendor.sh
#
# The output is written to src/chat_plugin/static/vendor.js and should
# be committed alongside any dependency-version changes.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OUT="$ROOT_DIR/src/chat_plugin/static/vendor.js"

cd "$ROOT_DIR"

# Install deps (creates a temporary node_modules)
echo "Installing vendor dependencies..."
npm install --no-save \
  preact@10 \
  htm@3 \
  marked@9 \
  dompurify@3 \
  esbuild@0.20

echo "Bundling vendor.js..."
npx esbuild scripts/vendor-entry.js \
  --bundle \
  --format=iife \
  --global-name=_vendor \
  --minify \
  --target=es2020 \
  --outfile="$OUT"

# Prepend header comment
HEADER="// vendor.js — vendored frontend bundle for amplifier-distro chat app
// Libraries: preact@10.x, htm@3.x, marked@9.x, dompurify@3.x
// Built: $(date -u +%Y-%m-%d)
// To rebuild: bash scripts/build-vendor.sh
"
TEMP=$(mktemp)
echo "$HEADER" > "$TEMP"
cat "$OUT" >> "$TEMP"
mv "$TEMP" "$OUT"

echo "Done → $OUT ($(wc -c < "$OUT" | tr -d ' ') bytes)"
