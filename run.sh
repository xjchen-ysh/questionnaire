#!/bin/bash

# 定义PID文件路径
PID_FILE="app.pid"

# 检查是否已有进程在运行
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "应用已在运行，PID: $OLD_PID"
        echo "如需重启，请先运行: kill $OLD_PID"
        exit 1
    else
        echo "清理旧的PID文件"
        rm -f "$PID_FILE"
    fi
fi

# 启动应用并记录PID
echo "启动应用..."
nohup uv run gunicorn -w 4 -b 0.0.0.0:5000 app:app > run.log 2>&1 &

# 获取后台进程的PID
APP_PID=$!

# 将PID写入文件
echo "$APP_PID" > "$PID_FILE"

echo "应用已启动，PID: $APP_PID"
echo "日志文件: run.log"
echo "PID文件: $PID_FILE"
echo ""
echo "停止应用命令: kill $APP_PID"
echo "或者: kill \$(cat $PID_FILE)"