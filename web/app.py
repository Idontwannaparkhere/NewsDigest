#!/usr/bin/env python3
"""
财政科学管理报告展示 Web 应用
"""

from flask import Flask, render_template
import os
import markdown
from datetime import datetime

app = Flask(__name__)
REPORTS_DIR = "output/reports"


def get_finance_reports():
    """获取所有财政科学管理报告，按日期排序"""
    reports = []
    if not os.path.exists(REPORTS_DIR):
        return reports

    for f in os.listdir(REPORTS_DIR):
        if f.startswith("finance-science-management-") and f.endswith(".md"):
            date_str = f.replace("finance-science-management-", "").replace(".md", "")
            filepath = os.path.join(REPORTS_DIR, f)

            # 读取概览信息
            overview = {}
            with open(filepath, "r", encoding="utf-8") as file:
                content = file.read()
                # 提取概览信息
                lines = content.split("\n")
                for line in lines:
                    if "文章总数:" in line or "文章总数：" in line:
                        overview["articles"] = line.split(":")[-1].strip().split(" ")[0]
                    elif "覆盖试点:" in line or "覆盖试点：" in line:
                        overview["pilots"] = line.split(":")[-1].strip().split(" ")[0]

            reports.append({
                "filename": f,
                "date": date_str,
                "path": filepath,
                "overview": overview
            })

    reports.sort(key=lambda x: x["date"], reverse=True)
    return reports


@app.route("/")
def index():
    """报告列表页"""
    reports = get_finance_reports()
    return render_template("index.html", reports=reports)


@app.route("/report/<filename>")
def report(filename):
    """报告详情页"""
    filepath = os.path.join(REPORTS_DIR, filename)
    if not os.path.exists(filepath):
        return "报告不存在", 404

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 渲染 Markdown
    html_content = markdown.markdown(
        content,
        extensions=["tables", "toc", "fenced_code"]
    )

    # 提取日期
    date_str = filename.replace("finance-science-management-", "").replace(".md", "")

    return render_template("report.html", content=html_content, date=date_str)


@app.route("/latest")
def latest():
    """跳转到最新报告"""
    reports = get_finance_reports()
    if reports:
        return f'<meta http-equiv="refresh" content="0;url=/report/{reports[0]["filename"]}">'
    return "暂无报告", 404


if __name__ == "__main__":
    print("启动财政科学管理报告展示系统...")
    print("访问 http://localhost:5000 查看报告列表")
    print("访问 http://localhost:5000/latest 直接查看最新报告")
    app.run(debug=True, port=5000)