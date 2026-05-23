#!/bin/zsh
set -euo pipefail

PORT="${SESSIONHUB_CHROME_PORT:-9222}"
PROFILE_DIR="${SESSIONHUB_CHROME_PROFILE:-$HOME/.sessionhub/chrome-9222}"
CHROME_APP="${SESSIONHUB_CHROME_APP:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
CHROME_BUNDLE="${SESSIONHUB_CHROME_BUNDLE:-Google Chrome}"

mkdir -p "$PROFILE_DIR"

if /usr/bin/curl -fsS "http://127.0.0.1:${PORT}/json/version" >/dev/null 2>&1; then
  echo "Chrome 9222 已运行：$PROFILE_DIR"
  exit 0
fi

/usr/bin/open -na "$CHROME_BUNDLE" --args \
  --remote-debugging-port="$PORT" \
  --user-data-dir="$PROFILE_DIR" \
  --no-first-run \
  --no-default-browser-check \
  --new-window \
  about:blank >/dev/null 2>&1

for _ in {1..20}; do
  if /usr/bin/curl -fsS "http://127.0.0.1:${PORT}/json/version" >/dev/null 2>&1; then
    echo "Chrome 9222 已启动：$PROFILE_DIR"
    exit 0
  fi
  sleep 0.5
done

echo "Chrome 9222 启动失败，请检查 Google Chrome 是否已安装。" >&2
exit 1
