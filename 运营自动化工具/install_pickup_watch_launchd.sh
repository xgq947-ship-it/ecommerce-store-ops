#!/bin/zsh
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
LABEL="com.xgq947.jst-pickup-watch"
SOURCE_PLIST="${PROJECT_DIR}/launchd/${LABEL}.plist"
AGENTS_DIR="${HOME}/Library/LaunchAgents"
TARGET_PLIST="${AGENTS_DIR}/${LABEL}.plist"

mkdir -p "$AGENTS_DIR" "${PROJECT_DIR}/logs"
ESCAPED_PROJECT_DIR="${PROJECT_DIR//\\/\\\\}"
ESCAPED_PROJECT_DIR="${ESCAPED_PROJECT_DIR//&/\\&}"
ESCAPED_PROJECT_DIR="${ESCAPED_PROJECT_DIR//|/\\|}"
sed "s|__PROJECT_DIR__|${ESCAPED_PROJECT_DIR}|g" "$SOURCE_PLIST" > "$TARGET_PLIST"

launchctl unload "$TARGET_PLIST" >/dev/null 2>&1 || true
launchctl load "$TARGET_PLIST"

echo "已安装聚水潭揽收监控 LaunchAgent：${LABEL}"
echo "查看状态：launchctl list | grep jst-pickup-watch"
echo "手动触发：launchctl kickstart -k gui/$(id -u)/${LABEL}"
