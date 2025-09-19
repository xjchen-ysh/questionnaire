#!/bin/bash

# 定义PID文件路径
PID_FILE="app.pid"

# 检查PID文件是否存在
if [ ! -f "$PID_FILE" ]; then
    echo "PID文件不存在，应用可能未运行"
    exit 1
fi

# 读取PID
APP_PID=$(cat "$PID_FILE")

# 检查进程是否存在
if ! ps -p "$APP_PID" > /dev/null 2>&1; then
    echo "进程 $APP_PID 不存在，清理PID文件"
    rm -f "$PID_FILE"
    exit 1
fi

# 停止进程
echo "正在停止应用，PID: $APP_PID"
kill "$APP_PID"

# 等待进程结束
sleep 2

# 检查进程是否已停止
if ps -p "$APP_PID" > /dev/null 2>&1; then
    echo "进程未正常停止，强制终止..."
    kill -9 "$APP_PID"
    sleep 1
fi

# 清理PID文件
rm -f "$PID_FILE"

echo "应用已停止"