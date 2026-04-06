#!/usr/bin/env python3
"""
财政科学管理资讯报告生成器 v3.0
按12项财政科学管理试点任务分类，生成Markdown报告
"""

import json
import os
import re
import yaml
from datetime import datetime, timedelta
from collections import defaultdict
from urllib.parse import quote

# 配置
TEMP_DIR = "output/temp"
OUTPUT_DIR = "output/reports"
DAYS_RANGE = 30  # 近30天

# 公众号与地区映射
ACCOUNT_REGION = {
    # 省级
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
    # 市级
    "深圳财政": "深圳市财政局", "广州财政": "广州市财政局",
    "杭州财政": "杭州市财政局", "南京财政": "南京市财政局",
    "武汉财政": "武汉市财政局", "成都财政": "成都市财政局",
    "西安财政": "西安市财政局", "苏州财政": "苏州市财政局",
    "青岛财政": "青岛市财政局", "宁波财政": "宁波市财政局",
    "厦门财政": "厦门市财政局", "郑州财政": "郑州市财政局",
    "长沙财政": "长沙市财政局", "合肥财政": "合肥市财政局",
    "济南财政": "济南市财政局",
}


def load_pilot_keywords():
    """加载试点任务关键词配置"""
    config_path = os.path.join(os.path.dirname(__file__), 'pilot_keywords.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config['pilot_tasks']


def load_json_files():
    """加载搜索结果JSON文件（合并微信和官网数据）"""
    articles = []
    pilot_tasks = []
    seen_titles = set()  # 用于去重

    # 官网来源名称列表（用于区分）
    website_sources = ['浙江省财政厅', '上海市财政局', '广东省财政厅', '江苏省财政厅',
                       '山东省财政厅', '河南省财政厅', '四川省财政厅', '湖北省财政厅',
                       '湖南省财政厅', '福建省财政厅', '安徽省财政厅', '河北省财政厅',
                       '陕西省财政厅', '辽宁省财政厅', '江西省财政厅', '云南省财政厅',
                       '贵州省财政厅', '甘肃省财政厅', '海南省财政厅', '天津市财政局',
                       '重庆市财政局', '北京市财政局', '吉林省财政厅', '黑龙江省财政厅',
                       '山西省财政厅', '内蒙古财政厅', '广西财政厅', '西藏财政厅',
                       '宁夏财政厅', '新疆财政厅', '青海省财政厅']

    # 加载微信文章
    wechat_path = os.path.join(TEMP_DIR, "finance-pilot-articles.json")
    if os.path.exists(wechat_path):
        try:
            with open(wechat_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                wechat_articles = data.get('articles', [])
                # 标记来源类型
                for a in wechat_articles:
                    # 根据来源名称判断类型
                    source = a.get('source', '')
                    if source in website_sources:
                        a['source_type'] = 'website'
                    else:
                        a['source_type'] = 'wechat'
                    title_key = re.sub(r'[^\w\u4e00-\u9fff]', '', a.get('title', '')).lower()
                    seen_titles.add(title_key)
                articles.extend(wechat_articles)
                pilot_tasks = data.get('pilot_tasks', [])
                print(f"微信文章: {len(wechat_articles)} 条")
        except Exception as e:
            print(f"Error loading {wechat_path}: {e}")

    # 加载官网文章
    website_path = os.path.join(TEMP_DIR, "finance-website-articles.json")
    if os.path.exists(website_path):
        try:
            with open(website_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                website_articles = data.get('articles', [])
                # 按标题去重（只添加微信没有的文章）
                added = 0
                for a in website_articles:
                    a['source_type'] = 'website'
                    title_key = re.sub(r'[^\w\u4e00-\u9fff]', '', a.get('title', '')).lower()
                    if title_key not in seen_titles:
                        articles.append(a)
                        seen_titles.add(title_key)
                        added += 1
                print(f"官网文章: {len(website_articles)} 条 (新增 {added} 条)")
        except Exception as e:
            print(f"Error loading {website_path}: {e}")

    print(f"总计: {len(articles)} 条")
    return articles, pilot_tasks


def filter_by_date(articles, days=DAYS_RANGE):
    """筛选近N天的文章"""
    now = datetime.now()
    cutoff = now - timedelta(days=days)

    filtered = []
    for article in articles:
        datetime_str = article.get('datetime', '')
        if not datetime_str:
            # 无时间的文章也保留（可能来自搜索结果）
            filtered.append(article)
            continue

        try:
            article_date = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
            if article_date >= cutoff:
                filtered.append(article)
        except:
            continue

    return filtered


def deduplicate(articles):
    """按标题去重"""
    seen_titles = set()
    unique = []

    for article in articles:
        title = article.get('title', '')
        # 简化标题用于比较
        title_simple = re.sub(r'[^\w\u4e00-\u9fff]', '', title)

        if title_simple and title_simple not in seen_titles:
            seen_titles.add(title_simple)
            unique.append(article)

    return unique


def classify_by_pilot_task(articles, pilot_tasks):
    """按试点任务分类"""
    task_articles = defaultdict(list)

    # 财政通用关键词（用于匹配一般财政新闻）
    general_keywords = ["财政", "预算", "资金", "支出", "收入", "税收", "专项", "补贴",
                        "拨款", "转移", "绩效", "债务", "债券", "国资", "监督", "改革",
                        "试点", "管理", "统筹", "体制", "政策", "民生", "基层", "会计",
                        "采购", "资产", "投资", "金融", "账户", "收费", "基金", "经费",
                        "财务", "审计", "税务", "票据", "公物", "国有资产", "政府采购",
                        "三公", "预算公开", "决算", "政府账本", "账本", "财经"]

    for article in articles:
        matched_tasks = article.get('matched_tasks', [])

        # 如果文章已经匹配了试点任务
        if matched_tasks:
            for match in matched_tasks:
                task_id = match['task_id']
                # 财政动态(task_id=0)转为-1，与未匹配区分
                if task_id == 0 and match.get('task_name') == '财政动态':
                    task_id = -1
                task_articles[task_id].append(article)
        else:
            # 未匹配任何试点任务，检查是否为一般财政新闻
            title = article.get('title', '')
            matched_general = False
            for kw in general_keywords:
                if kw in title:
                    task_articles[-1].append(article)
                    matched_general = True
                    break
            if not matched_general:
                task_articles[0].append(article)

    return task_articles


def generate_report(task_articles, pilot_tasks, date_str):
    """生成Markdown报告"""
    lines = []

    # 统计
    total_count = sum(len(articles) for task_id, articles in task_articles.items() if task_id not in [0, -1])
    finance_dynamic_count = len(task_articles.get(-1, []))
    unclassified_count = len(task_articles.get(0, []))
    covered_tasks = [task_id for task_id in task_articles if task_id not in [0, -1] and len(task_articles[task_id]) > 0]

    # 按来源统计
    wechat_official = 0  # 财政系统官方公众号
    wechat_media = 0    # 财政媒体公众号
    website_count = 0
    for task_id, articles in task_articles.items():
        for a in articles:
            if a.get('source_type') == 'website':
                website_count += 1
            elif a.get('is_official'):
                wechat_official += 1
            else:
                wechat_media += 1

    # 头部
    lines.append(f"# 财政科学管理资讯汇总 - {date_str}")
    lines.append("")
    lines.append("## 概览")
    lines.append("")
    lines.append(f"- 搜索时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- 时间范围: 近{DAYS_RANGE}天")
    lines.append(f"- 信息来源:")
    lines.append(f"  - 财政系统公众号: {wechat_official} 篇")
    if wechat_media > 0:
        lines.append(f"  - 财政媒体公众号: {wechat_media} 篇")
    lines.append(f"  - 省级财政厅官网: {website_count} 篇")
    lines.append(f"- 文章总数: {total_count} 篇")
    if finance_dynamic_count > 0:
        lines.append(f"- 财政动态: {finance_dynamic_count} 篇（官网一般财政新闻）")
    lines.append(f"- 覆盖试点: {len(covered_tasks)} 项")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 按试点任务输出
    pilot_dict = {task['id']: task for task in pilot_tasks}

    for task_id in sorted(covered_tasks):
        task = pilot_dict.get(task_id, {})
        task_name = task.get('name', f'试点{task_id}')
        articles = task_articles.get(task_id, [])

        lines.append(f"## 试点{task_id}: {task_name}")
        lines.append("")
        lines.append(f"匹配文章: {len(articles)} 篇")
        lines.append("")

        # 按时间排序，官方来源优先
        articles.sort(key=lambda x: (
            not x.get('is_official', False),
            x.get('datetime', '')
        ), reverse=True)

        for i, article in enumerate(articles, 1):
            title = article.get('title', '未知标题')
            url = article.get('url', '')
            source = article.get('source', '未知来源')
            region = article.get('region', '')
            datetime_str = article.get('datetime', '')
            summary = article.get('summary', '')
            source_type = article.get('source_type', 'wechat')
            is_official = article.get('is_official', False)
            matched_tasks = article.get('matched_tasks', [])

            # 来源标记: 官方公众号用 ✓, 媒体公众号用 ✬, 官网用 ◆
            if source_type == 'website':
                source_mark = "◆ "
            elif is_official:
                source_mark = "✓ "
            else:
                source_mark = "✬ "  # 媒体公众号

            # 匹配的关键词
            matched_keywords = [m.get('matched_keyword', '') for m in matched_tasks]
            keyword_str = matched_keywords[0] if matched_keywords else ''

            lines.append(f"### {i}. {source_mark}{title}")
            lines.append("")

            if region:
                lines.append(f"- 地区: **{region}**")
            lines.append(f"- 来源: {source}")

            if keyword_str:
                lines.append(f"- 匹配关键词: {keyword_str}")

            if url:
                # 处理相对路径链接
                if url.startswith('/link?'):
                    # 搜狗重定向链接，提供搜索入口
                    sogou_search = f"https://weixin.sogou.com/weixin?type=2&query={quote(title)}"
                    lines.append(f"- 链接: [搜狗搜索此文章]({sogou_search})")
                    lines.append(f"- 文章标题: {title}")
                else:
                    url_display = url if len(url) <= 60 else url[:60] + '...'
                    lines.append(f"- 链接: [{url_display}]({url})")

            if datetime_str:
                lines.append(f"- 时间: {datetime_str}")

            if summary:
                summary_short = summary[:100] + '...' if len(summary) > 100 else summary
                lines.append(f"- 摘要: {summary_short}")

            # 显示全文（如果有）
            content = article.get('content', '')
            if content:
                lines.append("")
                lines.append("<details>")
                lines.append("<summary>📖 查看全文</summary>")
                lines.append("")
                lines.append(content)
                lines.append("")
                lines.append("</details>")

            lines.append("")

        lines.append("---")
        lines.append("")

    # 财政动态（官网一般财政新闻）
    if finance_dynamic_count > 0:
        lines.append("## 财政动态")
        lines.append("")
        lines.append("以下为各地财政厅官网的一般财政新闻，虽未直接匹配试点任务关键词，但与财政工作相关：")
        lines.append(f"共 {finance_dynamic_count} 篇")
        lines.append("")

        dynamic_articles = task_articles.get(-1, [])
        # 按来源分组显示
        from collections import defaultdict
        by_source = defaultdict(list)
        for a in dynamic_articles:
            by_source[a.get('source', '未知')].append(a)

        for source, items in sorted(by_source.items()):
            lines.append(f"### {source} ({len(items)} 条)")
            lines.append("")
            for i, article in enumerate(items[:10], 1):  # 每个来源最多显示10条
                title = article.get('title', '未知标题')
                url = article.get('url', '')
                datetime_str = article.get('datetime', '')
                keyword_str = ''
                for m in article.get('matched_tasks', []):
                    if m.get('matched_keyword'):
                        keyword_str = m.get('matched_keyword')
                        break

                lines.append(f"{i}. ◆ {title}")
                if url:
                    url_display = url if len(url) <= 50 else url[:50] + '...'
                    lines.append(f"   链接: [{url_display}]({url})")
                if datetime_str:
                    lines.append(f"   时间: {datetime_str}")
                lines.append("")
            lines.append("")

        lines.append("---")
        lines.append("")

    # 未分类文章
    if unclassified_count > 0:
        lines.append("## 未匹配试点任务的文章")
        lines.append("")
        lines.append(f"共 {unclassified_count} 篇")
        lines.append("")

        unclassified = task_articles.get(0, [])
        unclassified.sort(key=lambda x: (
            not x.get('is_official', False),
            x.get('datetime', '')
        ), reverse=True)

        for i, article in enumerate(unclassified[:20], 1):  # 最多显示20篇
            title = article.get('title', '未知标题')
            source = article.get('source', '')
            source_type = article.get('source_type', 'wechat')
            is_official = article.get('is_official', False)

            if source_type == 'website':
                source_mark = "◆ "
            elif is_official:
                source_mark = "✓ "
            else:
                source_mark = "✬ "

            lines.append(f"{i}. {source_mark}{title} ({source})")

        lines.append("")
        lines.append("---")
        lines.append("")

    # 尾部
    lines.append("## 说明")
    lines.append("")
    lines.append("- ✓ 标记表示来自财政系统官方公众号")
    lines.append("- ✬ 标记表示来自财政媒体公众号")
    lines.append("- ◆ 标记表示来自省级财政厅官网")
    lines.append("- 文章按试点任务分类，一篇文章可能匹配多个试点任务")
    lines.append(f"- 覆盖的{len(covered_tasks)}项试点: {', '.join([pilot_dict.get(t, {}).get('name', '') for t in covered_tasks])}")
    lines.append("")
    lines.append("### 如何查看文章")
    lines.append("")
    lines.append("**微信公众号文章:**")
    lines.append("1. 点击「搜狗搜索此文章」链接")
    lines.append("2. 在搜狗搜索结果页面中点击对应的文章标题")
    lines.append("3. 即可跳转到微信公众号原文")
    lines.append("")
    lines.append("**官网文章:**")
    lines.append("1. 直接点击文章链接")
    lines.append("2. 即可跳转到财政厅官网原文")
    lines.append("")
    lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return '\n'.join(lines)


def main():
    # 加载数据
    print("加载搜索结果...")
    articles, pilot_tasks = load_json_files()

    if not articles:
        print("未找到搜索结果")
        return

    # 加载关键词配置（如果JSON中没有）
    if not pilot_tasks:
        pilot_tasks = load_pilot_keywords()

    # 筛选时间
    print(f"筛选近{DAYS_RANGE}天文章...")
    filtered = filter_by_date(articles)
    print(f"筛选后 {len(filtered)} 条")

    # 去重
    print("去重...")
    unique = deduplicate(filtered)
    print(f"去重后 {len(unique)} 条")

    # 按试点任务分类
    print("按试点任务分类...")
    task_articles = classify_by_pilot_task(unique, pilot_tasks)

    # 分类统计
    finance_dynamic_count = len(task_articles.get(-1, []))  # 财政动态(task_id=0被转为-1)
    unclassified_count = len(task_articles.get(0, []))

    for task_id, items in task_articles.items():
        task_name = ""
        if task_id == -1:
            task_name = "财政动态"
        elif task_id == 0:
            task_name = "未匹配"
        elif task_id > 0:
            task = next((t for t in pilot_tasks if t['id'] == task_id), None)
            task_name = task.get('name', '') if task else f"试点{task_id}"
        print(f"  {task_name}: {len(items)} 条")

    # 生成报告
    print("生成报告...")
    date_str = datetime.now().strftime('%Y-%m-%d')
    report = generate_report(task_articles, pilot_tasks, date_str)

    # 保存
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = f"{OUTPUT_DIR}/finance-science-management-{date_str}.md"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"报告已保存: {output_path}")


if __name__ == "__main__":
    main()