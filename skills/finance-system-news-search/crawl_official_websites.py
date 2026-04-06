#!/usr/bin/env python3
"""
财政厅官网资讯爬取脚本 v1.0
从省级财政厅官网获取近10天新闻资讯
"""

import requests
import yaml
import json
import os
import re
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from tqdm import tqdm

# 配置
TEMP_DIR = "output/temp"
CONFIG_FILE = "skills/finance-system-news-search/official_websites.yaml"
PILOT_TASKS_FILE = "skills/finance-system-news-search/附件2-财政科学管理试点任务详情.md"
DAYS_RANGE = 10

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

# 请求超时和重试配置
TIMEOUT = 15
MAX_RETRIES = 2


def load_website_config():
    """加载官网配置"""
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_pilot_tasks():
    """从markdown文件加载试点任务和关键词"""
    pilot_tasks = []

    if not os.path.exists(PILOT_TASKS_FILE):
        return pilot_tasks

    with open(PILOT_TASKS_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    current_task = None
    task_id = 0

    for line in lines:
        line = line.strip()

        if line.startswith('## ') and not line.startswith('## 财政科学管理试点'):
            task_id += 1
            task_name = line[3:].strip()
            current_task = {
                'id': task_id,
                'name': task_name,
                'keywords': []
            }
            pilot_tasks.append(current_task)

        elif line.startswith('### ') and current_task:
            measure = line[4:].strip()
            measure = re.sub(r'^\d+\.', '', measure).strip()
            if measure and len(measure) > 2:
                current_task['keywords'].append(measure)

    # 补充核心关键词
    task_keywords_map = {
        1: ["预算统筹", "全口径预算", "四本预算", "存量资金", "存量资产", "预算分配", "财政资源", "资金统筹", "预算管理"],
        2: ["过紧日子", "三公经费", "一般性支出", "厉行节约", "节支", "压减支出", "严控支出", "节约", "紧日子"],
        3: ["零基预算", "支出定额", "项目评估", "打破基数", "预算编制", "零基", "项目库"],
        4: ["财政承受能力", "预算管理链条", "预算执行", "预算单位", "预算调整", "预算批复"],
        5: ["绩效评价", "绩效管理", "成本效益", "事前绩效", "绩效目标", "绩效结果", "绩效", "评价"],
        6: ["转移支付", "财政体制", "省以下财政", "市县财政", "财力下沉", "财政事权", "支出责任"],
        7: ["国有资本", "国有资本经营预算", "国有企业收益", "国资预算", "国资经营"],
        8: ["三保", "基本民生", "保工资", "保运转", "基层财政", "兜底", "民生保障"],
        9: ["地方政府债务", "隐性债务", "专项债券", "化债", "债务风险", "债券", "债务管理", "专项债"],
        10: ["财会监督", "会计监督", "财经纪律", "监督检查", "监督", "会计信息"],
        11: ["预算管理一体化", "财政数字化", "数字财政", "财政信息化", "一体化", "信息化", "数字化"],
        12: ["人工智能财政", "AI财政", "智能财政", "大模型", "人工智能", "智能化"],
    }

    # 额外的财政通用关键词（用于匹配一般财政新闻）
    general_keywords = ["财政", "预算", "资金", "支出", "收入", "税收", "专项", "补贴",
                        "拨款", "转移", "绩效", "债务", "债券", "国资", "监督", "改革",
                        "试点", "管理", "统筹", "体制", "政策", "民生", "基层"]

    for task in pilot_tasks:
        tid = task['id']
        if tid in task_keywords_map:
            existing = set(task['keywords'])
            for kw in task_keywords_map[tid]:
                if kw not in existing:
                    task['keywords'].append(kw)

    return pilot_tasks


def match_pilot_task(title, pilot_tasks):
    """匹配文章对应的试点任务"""
    matched = []
    title_lower = title.lower()

    # 财政通用关键词（匹配一般财政新闻）
    general_keywords = ["财政", "预算", "资金", "支出", "收入", "税收", "专项", "补贴",
                        "拨款", "转移", "绩效", "债务", "债券", "国资", "监督", "改革",
                        "试点", "管理", "统筹", "体制", "政策", "民生", "基层", "会计",
                        "采购", "资产", "投资", "金融", "账户", "收费", "基金", "经费",
                        "财务", "审计", "税务", "票据", "公物", "国有资产", "政府采购",
                        "三公", "预算公开", "决算", "政府账本", "账本", "财经"]

    for task in pilot_tasks:
        for keyword in task['keywords']:
            if keyword.lower() in title_lower:
                matched.append({
                    'task_id': task['id'],
                    'task_name': task['name'],
                    'matched_keyword': keyword
                })
                break

    # 如果没匹配到试点任务，检查是否为一般财政新闻
    if not matched:
        for kw in general_keywords:
            if kw in title:
                matched.append({
                    'task_id': 0,
                    'task_name': '财政动态',
                    'matched_keyword': kw
                })
                break

    return matched


def extract_date(text):
    """从文本中提取日期"""
    if not text:
        return None

    text = text.strip()

    # 多种日期格式
    patterns = [
        (r'\d{4}-\d{1,2}-\d{1,2}', '%Y-%m-%d'),
        (r'\d{4}/\d{1,2}/\d{1,2}', '%Y/%m/%d'),
        (r'\d{4}年\d{1,2}月\d{1,2}日', '%Y年%m月%d日'),
        (r'\d{1,2}-\d{1,2}$', None),  # 仅月-日
    ]

    for pattern, fmt in patterns:
        match = re.search(pattern, text)
        if match:
            date_str = match.group()
            if fmt:
                try:
                    # 处理年月日格式
                    if '年' in date_str:
                        date_str = date_str.replace('年', '-').replace('月', '-').replace('日', '')
                        return date_str
                    return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
                except:
                    continue
            elif '-' in date_str and len(date_str) <= 5:
                # 补充年份
                parts = date_str.split('-')
                year = datetime.now().year
                return f"{year}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"

    return None


def is_recent(date_str, days=DAYS_RANGE):
    """判断日期是否在近N天内"""
    if not date_str:
        return False

    try:
        article_date = datetime.strptime(date_str, '%Y-%m-%d')
        cutoff = datetime.now() - timedelta(days=days)
        return article_date >= cutoff
    except:
        return False


def normalize_url(url, base_url):
    """规范化URL"""
    if not url:
        return ''
    if url.startswith('http'):
        return url
    return urljoin(base_url, url)


def is_same_domain(url, base_url):
    """检查URL是否与base_url同域名"""
    if not url or not base_url:
        return False
    try:
        from urllib.parse import urlparse
        url_domain = urlparse(url).netloc
        base_domain = urlparse(base_url).netloc
        # 允许子域名，如 www.czt.gd.gov.cn 和 czt.gd.gov.cn
        return url_domain == base_domain or url_domain.endswith('.' + base_domain) or base_domain.endswith('.' + url_domain)
    except:
        return False


def detect_news_columns(soup, base_url):
    """从首页自动探测新闻栏目"""
    columns = []
    column_keywords = ['新闻', '动态', '公告', '通知', '政务', '公开', '工作', '要闻', '资讯']

    # 查找导航菜单中的链接
    nav_selectors = ['nav', '.nav', '.menu', '#menu', '.navbar', '.header-nav', '.navigation']

    for nav_sel in nav_selectors:
        nav = soup.select_one(nav_sel)
        if nav:
            for link in nav.find_all('a', href=True):
                text = link.get_text(strip=True)
                href = link.get('href', '')

                for kw in column_keywords:
                    if kw in text and len(text) < 20:
                        full_url = normalize_url(href, base_url)
                        if full_url and full_url not in [c['url'] for c in columns]:
                            columns.append({
                                'name': text,
                                'url': full_url
                            })
                        break

    # 如果没找到导航，查找首页可能的新闻列表区域
    if not columns:
        list_selectors = ['.news', '.news-list', '.list', '.article-list', '#news']
        for sel in list_selectors:
            container = soup.select_one(sel)
            if container:
                # 尝试从容器中的链接提取
                parent_link = container.find_parent('a')
                if parent_link and parent_link.get('href'):
                    columns.append({
                        'name': '新闻动态',
                        'url': normalize_url(parent_link.get('href'), base_url)
                    })
                    break

    return columns[:5]  # 最多5个栏目


def parse_list_page(soup, base_url):
    """解析新闻列表页"""
    articles = []

    # 无效标题关键词（导航/栏目名）
    invalid_keywords = ['首页', '导航', '机构', '概况', '政务公开', '信息公开',
                        '办事服务', '联系方式', '下载', '搜索', '登录', '注册',
                        '信用信息', '双公示', '地市财政', '重点领域', '服务窗口',
                        '年度报表', '工作报表', '网站工作', '行政执法', '政务服务',
                        '实施清单', '支付平台', '公共服务', '专题', '报表']

    # 非财政机构关键词（过滤掉爬取到的其他政府部门链接）
    exclude_organizations = ['国家中医药管理局', '药品监督管理局', '卫健委', '医疗保障局',
                             '人力资源和社会保障局', '教育局', '科技局', '工信局',
                             '发改委', '发展和改革委员会', '统计局', '审计局',
                             '市场监督管理局', '税务局', '公安厅', '民政厅']

    # 多种常见的列表结构选择器
    list_patterns = [
        ('.news-list li', 'a', '.date, .time, span'),
        ('ul.news li', 'a', '.date, .time, span'),
        ('ul.list li', 'a', '.date, .time, span'),
        ('.article-list li', 'a, .title a', '.date, .time'),
        ('.list-item', 'a, .title a', '.date, .time'),
        ('table tr', 'td a', 'td'),
        ('.gl_list li', 'a', 'span'),
        ('li.news-item', 'a', '.date'),
        ('.zhengwu-list li', 'a', 'span'),
        ('.news-box li', 'a', '.date'),
        ('.content-list li', 'a', '.date'),
        ('ul.gzdt li', 'a', 'span'),
    ]

    for list_sel, title_sel, date_sel in list_patterns:
        items = soup.select(list_sel)
        if items and len(items) > 2:
            for item in items:
                title_elem = item.select_one(title_sel)
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                href = title_elem.get('href', '')

                # 过滤无效标题
                if not title or len(title) < 8:
                    continue
                # 过滤导航/栏目名称
                if any(kw in title for kw in invalid_keywords):
                    continue
                # 过滤非财政机构
                if any(org in title for org in exclude_organizations):
                    continue
                # 过滤乱码标题（包含过多非中文/英文字符）
                chinese_count = len(re.findall(r'[\u4e00-\u9fff]', title))
                if chinese_count < len(title) * 0.3 and len(title) > 10:
                    continue

                # 提取日期
                date_elem = item.select_one(date_sel)
                date_str = None
                if date_elem:
                    date_str = extract_date(date_elem.get_text())

                # 也可以从标题链接的URL中提取日期
                if not date_str and href:
                    date_str = extract_date(href)

                full_url = normalize_url(href, base_url)
                # 过滤外部链接（只保留当前网站域名的链接）
                if not is_same_domain(full_url, base_url):
                    continue

                articles.append({
                    'title': title,
                    'url': full_url,
                    'date': date_str
                })

            if articles:
                return articles

    # 如果上述模式都没匹配，尝试通用的li元素
    for li in soup.find_all('li'):
        link = li.find('a', href=True)
        if link:
            title = link.get_text(strip=True)
            # 过滤无效标题
            if not title or len(title) < 8:
                continue
            if any(kw in title for kw in invalid_keywords):
                continue
            if any(org in title for org in exclude_organizations):
                continue
            chinese_count = len(re.findall(r'[\u4e00-\u9fff]', title))
            if chinese_count < len(title) * 0.3 and len(title) > 10:
                continue

            full_url = normalize_url(link.get('href'), base_url)
            # 过滤外部链接
            if not is_same_domain(full_url, base_url):
                continue

            date_str = extract_date(li.get_text())
            articles.append({
                'title': title,
                'url': full_url,
                'date': date_str
            })

    return articles[:30]  # 每个栏目最多30条


def crawl_site_quiet(site_config, pilot_tasks):
    """静默爬取单个财政厅官网（用于进度条模式）"""
    articles = []
    name = site_config['name']
    base_url = site_config['url']

    try:
        # 访问首页
        resp = requests.get(base_url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        # 自动检测编码
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, 'html.parser')

        # 探测新闻栏目
        columns = detect_news_columns(soup, base_url)
        if not columns:
            columns = [{'name': '首页', 'url': base_url}]

        # 爬取各栏目
        for column in columns[:3]:
            try:
                time.sleep(0.3)
                col_url = column['url']
                if col_url == base_url:
                    col_soup = soup
                else:
                    col_resp = requests.get(col_url, headers=HEADERS, timeout=TIMEOUT)
                    col_resp.encoding = col_resp.apparent_encoding
                    col_soup = BeautifulSoup(col_resp.text, 'html.parser')

                items = parse_list_page(col_soup, base_url)

                for item in items:
                    date_str = item.get('date')
                    if date_str and not is_recent(date_str):
                        continue

                    matched = match_pilot_task(item['title'], pilot_tasks)

                    article = {
                        'title': item['title'],
                        'url': item['url'],
                        'source': name,
                        'source_type': 'website',
                        'region': site_config.get('region', ''),
                        'datetime': date_str or '',
                        'is_official': True,
                        'matched_tasks': matched,
                        'crawl_metadata': {
                            'column_name': column['name'],
                            'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                    }
                    articles.append(article)

            except Exception:
                pass

        # 去重
        seen_titles = set()
        unique_articles = []
        for a in articles:
            title_key = re.sub(r'[^\w\u4e00-\u9fff]', '', a['title'])
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_articles.append(a)

        return unique_articles

    except Exception:
        return []


def crawl_site(site_config, pilot_tasks):
    """爬取单个财政厅官网"""
    articles = []
    name = site_config['name']
    base_url = site_config['url']

    print(f"\n爬取: {name} ({base_url})")

    try:
        # 访问首页
        resp = requests.get(base_url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        # 自动检测编码
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, 'html.parser')

        # 探测新闻栏目
        columns = detect_news_columns(soup, base_url)

        if not columns:
            print(f"  未探测到新闻栏目，尝试直接解析首页")
            columns = [{'name': '首页', 'url': base_url}]

        # 爬取各栏目
        for column in columns[:3]:
            try:
                time.sleep(0.5)  # 避免请求过快

                col_url = column['url']
                if col_url == base_url:
                    col_soup = soup
                else:
                    col_resp = requests.get(col_url, headers=HEADERS, timeout=TIMEOUT)
                    col_resp.encoding = col_resp.apparent_encoding
                    col_soup = BeautifulSoup(col_resp.text, 'html.parser')

                # 解析列表
                items = parse_list_page(col_soup, base_url)

                for item in items:
                    # 筛选近10天
                    date_str = item.get('date')
                    if date_str and not is_recent(date_str):
                        continue

                    # 匹配试点任务关键词
                    matched = match_pilot_task(item['title'], pilot_tasks)

                    article = {
                        'title': item['title'],
                        'url': item['url'],
                        'source': name,
                        'source_type': 'website',
                        'region': site_config.get('region', ''),
                        'datetime': date_str or '',
                        'is_official': True,
                        'matched_tasks': matched,
                        'crawl_metadata': {
                            'column_name': column['name'],
                            'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                    }
                    articles.append(article)

                print(f"  {column['name']}: {len(items)} 条")

            except Exception as e:
                print(f"  栏目 {column['name']} 爬取失败: {str(e)[:30]}")

        # 去重
        seen_titles = set()
        unique_articles = []
        for a in articles:
            title_key = re.sub(r'[^\w\u4e00-\u9fff]', '', a['title'])
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_articles.append(a)

        print(f"  总计: {len(unique_articles)} 条相关文章")
        return unique_articles

    except Exception as e:
        print(f"  爬取失败: {str(e)[:50]}")
        return []


def main():
    """主入口"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始爬取省级财政厅官网...")

    os.makedirs(TEMP_DIR, exist_ok=True)

    # 加载配置
    config = load_website_config()
    pilot_tasks = load_pilot_tasks()

    if not pilot_tasks:
        print("警告: 未加载到试点任务关键词")
        return None

    print(f"加载 {len(pilot_tasks)} 项试点任务关键词")

    all_articles = []
    sites = config['省级']

    # 使用进度条爬取各省级网站
    print(f"\n爬取 {len(sites)} 个省级财政厅官网:")
    for site in tqdm(sites, desc="官网爬取进度", unit="网站", ncols=80):
        articles = crawl_site_quiet(site, pilot_tasks)
        all_articles.extend(articles)
        time.sleep(0.5)  # 网站间间隔

    # 统计
    task_counts = {}
    for article in all_articles:
        for match in article.get('matched_tasks', []):
            task_id = match['task_id']
            task_counts[task_id] = task_counts.get(task_id, 0) + 1

    print(f"\n=== 爬取完成 ===")
    print(f"共收集 {len(all_articles)} 条文章")
    print(f"\n各试点任务文章分布:")
    pilot_dict = {t['id']: t['name'] for t in pilot_tasks}
    for task_id in sorted(task_counts.keys()):
        print(f"  试点{task_id} ({pilot_dict.get(task_id, '')}): {task_counts[task_id]} 条")

    # 保存
    output_data = {
        'source': 'official_websites',
        'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total': len(all_articles),
        'articles': all_articles
    }

    filepath = os.path.join(TEMP_DIR, "finance-website-articles.json")
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n数据已保存: {filepath}")
    return filepath


if __name__ == "__main__":
    main()