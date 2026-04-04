#!/usr/bin/env python3
"""
财政科学管理资讯搜索脚本 v5.0
从试点任务详情文件读取关键词，搜索相关资讯
"""

import requests
import json
import time
import os
import re
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import quote

# 配置
TEMP_DIR = "output/temp"
OUTPUT_DIR = "output/reports"
PILOT_TASKS_FILE = "skills/finance-system-news-search/附件2-财政科学管理试点任务详情.md"

# 所有公众号列表
ACCOUNTS = [
    # 省级财政厅
    "浙江财政", "上海财政", "北京财政", "广东财政", "江苏财政",
    "山东财政", "河南财政", "四川财政", "湖北财政", "湖南财政",
    "福建财政", "安徽财政", "河北财政", "陕西财政", "辽宁财政",
    "江西财政", "云南财政", "贵州财政", "甘肃财政", "海南财政",
    "天津财政", "重庆财政",
    # 市级财政局
    "深圳财政", "广州财政", "杭州财政", "南京财政", "武汉财政",
    "成都财政", "西安财政", "苏州财政", "青岛财政", "宁波财政",
    "厦门财政", "郑州财政", "长沙财政", "合肥财政", "济南财政",
]

# 公众号与地区映射
ACCOUNT_REGION = {
    "浙江财政": "浙江省财政厅", "上海财政": "上海市财政局",
    "北京财政": "北京市财政局", "广东财政": "广东省财政厅",
    "江苏财政": "江苏省财政厅", "山东财政": "山东省财政厅",
    "河南财政": "河南省财政厅", "四川财政": "四川省财政厅",
    "湖北财政": "湖北省财政厅", "湖南财政": "湖南省财政厅",
    "福建财政": "福建省财政厅", "安徽财政": "安徽省财政厅",
    "河北财政": "河北省财政厅", "陕西财政": "陕西省财政厅",
    "辽宁财政": "辽宁省财政厅", "江西财政": "江西省财政厅",
    "云南财政": "云南省财政厅", "贵州财政": "贵州省财政厅",
    "甘肃财政": "甘肃省财政厅", "海南财政": "海南省财政厅",
    "天津财政": "天津市财政局", "重庆财政": "重庆市财政局",
    "深圳财政": "深圳市财政局", "广州财政": "广州市财政局",
    "杭州财政": "杭州市财政局", "南京财政": "南京市财政局",
    "武汉财政": "武汉市财政局", "成都财政": "成都市财政局",
    "西安财政": "西安市财政局", "苏州财政": "苏州市财政局",
    "青岛财政": "青岛市财政局", "宁波财政": "宁波市财政局",
    "厦门财政": "厦门市财政局", "郑州财政": "郑州市财政局",
    "长沙财政": "长沙市财政局", "合肥财政": "合肥市财政局",
    "济南财政": "济南市财政局",
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}


def load_pilot_tasks_from_md():
    """从markdown文件加载试点任务和关键词"""
    pilot_tasks = []

    if not os.path.exists(PILOT_TASKS_FILE):
        print(f"警告: 找不到试点任务文件 {PILOT_TASKS_FILE}")
        return pilot_tasks

    with open(PILOT_TASKS_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # 解析markdown，提取试点任务
    lines = content.split('\n')
    current_task = None
    task_id = 0

    for line in lines:
        line = line.strip()

        # 匹配试点任务标题 (## 开头)
        if line.startswith('## ') and not line.startswith('## 财政科学管理试点'):
            task_id += 1
            task_name = line[3:].strip()
            current_task = {
                'id': task_id,
                'name': task_name,
                'keywords': [],
                'content': ''
            }
            pilot_tasks.append(current_task)

        # 匹配试点内容
        elif line.startswith('**试点内容**:') and current_task:
            content = line.replace('**试点内容**:', '').strip()
            current_task['content'] = content

        # 匹配措施标题 (### 开头)，提取关键词
        elif line.startswith('### ') and current_task:
            # 提取措施标题作为关键词
            measure = line[4:].strip()
            # 去掉序号
            measure = re.sub(r'^\d+\.', '', measure).strip()
            if measure and len(measure) > 2:
                current_task['keywords'].append(measure)

    # 为每个任务补充核心关键词（从任务名称和内容中提取）
    task_keywords_map = {
        1: ["预算统筹", "全口径预算", "四本预算", "存量资金", "存量资产", "预算分配"],
        2: ["过紧日子", "三公经费", "一般性支出", "厉行节约", "节支"],
        3: ["零基预算", "支出定额", "项目评估", "预算编制", "打破基数"],
        4: ["财政承受能力", "预算管理链条", "预算执行", "预算单位"],
        5: ["绩效评价", "绩效管理", "成本效益", "绩效评估", "事前绩效"],
        6: ["转移支付", "财政体制", "省以下财政", "市县财政", "财力下沉"],
        7: ["国有资本", "国有资本经营预算", "国有企业收益", "国资预算"],
        8: ["三保", "基本民生", "保工资", "保运转", "基层财政"],
        9: ["地方政府债务", "隐性债务", "专项债券", "债务风险", "化债"],
        10: ["财会监督", "会计监督", "财经纪律", "监督检查"],
        11: ["预算管理一体化", "财政数字化", "数字财政", "财政信息化"],
        12: ["人工智能财政", "AI财政", "智能财政", "大模型财政"],
    }

    for task in pilot_tasks:
        tid = task['id']
        if tid in task_keywords_map:
            # 合并预设关键词和提取的关键词
            existing = set(task['keywords'])
            for kw in task_keywords_map[tid]:
                if kw not in existing:
                    task['keywords'].append(kw)

    return pilot_tasks


def get_priority_keywords(pilot_tasks):
    """获取高优先级关键词（每个任务取前5个最核心关键词）"""
    keywords = []
    for task in pilot_tasks:
        keywords.extend(task['keywords'][:5])
    return keywords


def search_sogou_wechat(query, max_results=10):
    """使用搜狗微信搜索"""
    url = f"https://weixin.sogou.com/weixin?type=2&query={quote(query)}"
    articles = []

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, 'html.parser')

        for item in soup.select('.news-list li')[:max_results]:
            title_elem = item.select_one('.txt-box h3 a')
            if not title_elem:
                continue

            title = title_elem.get_text(strip=True)
            link = title_elem.get('href', '')

            desc_elem = item.select_one('.txt-box p')
            summary = desc_elem.get_text(strip=True) if desc_elem else ''

            source_elem = item.select_one('.s-p .account')
            source = source_elem.get_text(strip=True) if source_elem else ''

            time_elem = item.select_one('.s-p .s2')
            datetime_str = time_elem.get_text(strip=True) if time_elem else ''

            if 'timeConvert' in str(time_elem):
                match = re.search(r"timeConvert\('(\d+)'", str(time_elem))
                if match:
                    ts = int(match.group(1))
                    datetime_str = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

            articles.append({
                'title': title,
                'url': link,
                'summary': summary,
                'source': source,
                'datetime': datetime_str,
            })

    except Exception as e:
        pass

    return articles


def match_pilot_task(article, pilot_tasks):
    """匹配文章对应的试点任务"""
    text = (article.get('title', '') + ' ' + article.get('summary', '')).lower()
    matched_tasks = []

    for task in pilot_tasks:
        for keyword in task['keywords']:
            if keyword.lower() in text:
                matched_tasks.append({
                    'task_id': task['id'],
                    'task_name': task['name'],
                    'matched_keyword': keyword
                })
                break

    return matched_tasks


def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始搜索财政科学管理资讯...")

    os.makedirs(TEMP_DIR, exist_ok=True)

    # 清理临时文件
    for f in os.listdir(TEMP_DIR):
        if f.startswith('finance-') and f.endswith('.json'):
            os.remove(os.path.join(TEMP_DIR, f))

    # 从markdown文件加载试点任务
    pilot_tasks = load_pilot_tasks_from_md()
    if not pilot_tasks:
        print("错误: 未能加载试点任务")
        return

    priority_keywords = get_priority_keywords(pilot_tasks)
    print(f"加载 {len(pilot_tasks)} 项试点任务，{len(priority_keywords)} 个核心关键词")

    seen_urls = set()
    all_articles = []
    year = datetime.now().year

    # 搜狗微信搜索
    print("\n搜狗微信搜索...")
    for account in ACCOUNTS:
        print(f"\n搜索: {account}")
        for keyword in priority_keywords[:6]:
            query = f"{account} {keyword} {year}"
            articles = search_sogou_wechat(query, max_results=5)

            for article in articles:
                url_key = article['url'][-50:] if article['url'] else article['title']
                if url_key in seen_urls:
                    continue
                seen_urls.add(url_key)

                article['source'] = account
                article['region'] = ACCOUNT_REGION.get(account, '')
                article['is_official'] = True

                matched = match_pilot_task(article, pilot_tasks)
                article['matched_tasks'] = matched

                if matched:
                    all_articles.append(article)

            time.sleep(1.5)

    print(f"\n共收集 {len(all_articles)} 篇相关文章")

    # 统计各试点文章数
    task_counts = {}
    for article in all_articles:
        for match in article.get('matched_tasks', []):
            task_id = match['task_id']
            task_counts[task_id] = task_counts.get(task_id, 0) + 1

    print("\n各试点任务文章分布:")
    pilot_dict = {t['id']: t['name'] for t in pilot_tasks}
    for task_id in sorted(task_counts.keys()):
        print(f"  试点{task_id} ({pilot_dict.get(task_id, '')}): {task_counts[task_id]} 篇")

    # 保存到临时文件
    output_file = os.path.join(TEMP_DIR, "finance-pilot-articles.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total': len(all_articles),
            'pilot_tasks': pilot_tasks,
            'articles': all_articles
        }, f, ensure_ascii=False, indent=2)

    print(f"\n数据已保存: {output_file}")

    # 调用报告生成脚本
    print("\n生成报告...")
    os.system("python3 skills/finance-system-news-search/generate_report.py")

    print(f"\n报告路径: {OUTPUT_DIR}/finance-science-management-{datetime.now().strftime('%Y-%m-%d')}.md")


if __name__ == "__main__":
    main()