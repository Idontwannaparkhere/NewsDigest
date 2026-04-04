#!/bin/bash
# 财政系统新闻搜索脚本 v2.0
# 使用 cn-web-search 的必应公众号索引搜索

set -e

DATE=$(date +%Y-%m-%d)
TIME=$(date "+%Y-%m-%d %H:%M:%S")
OUTPUT_DIR="output/reports"

echo "[$TIME] 开始搜索财政系统新闻..."

# 运行 Python 搜索脚本
python3 skills/finance-system-news-search/search.py

echo "[$(date "+%H:%M:%S")] 搜索完成"
echo "报告路径: $OUTPUT_DIR/finance-system-news-$DATE.md"