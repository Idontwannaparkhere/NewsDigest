#!/bin/bash
# 启动财政科学管理报告展示系统

cd "$(dirname "$0")"

echo "安装依赖..."
pip install -q flask markdown

echo "启动 Web 服务..."
echo "访问 http://localhost:5000 查看报告列表"
echo "访问 http://localhost:5000/latest 直接查看最新报告"
echo ""
echo "按 Ctrl+C 停止服务"

python web/app.py