#!/bin/bash

echo "正在重启应用..."

# 停止应用
./stop.sh

# 等待一秒确保进程完全停止
sleep 1

# 启动应用
./run.sh

echo "重启完成"