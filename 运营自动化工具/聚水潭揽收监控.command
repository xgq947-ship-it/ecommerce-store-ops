#!/bin/zsh
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

echo "开始执行聚水潭揽收监控..."
python3 run.py 聚水潭揽收监控 --notify
STATUS=$?
echo ""
echo "执行完成（退出码：${STATUS}），按任意键关闭窗口..."
read -k 1
echo ""
exit "$STATUS"
