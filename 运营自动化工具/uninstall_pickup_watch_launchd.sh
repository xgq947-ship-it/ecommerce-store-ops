#!/bin/zsh
set -euo pipefail

LABEL="com.xgq947.jst-pickup-watch"
TARGET_PLIST="${HOME}/Library/LaunchAgents/${LABEL}.plist"

if [[ -f "$TARGET_PLIST" ]]; then
    launchctl unload "$TARGET_PLIST" >/dev/null 2>&1 || true
    rm -f "$TARGET_PLIST"
fi

echo "已卸载聚水潭揽收监控 LaunchAgent：${LABEL}"
