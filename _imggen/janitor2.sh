#!/bin/bash
while pgrep -f "redo.sh|viewer_review" > /dev/null; do
  find "$HOME/.codex/generated_images" -mindepth 1 -maxdepth 1 -mmin +5 -exec rm -rf {} + 2>/dev/null
  sleep 120
done
