"""
NewsDigest - 资讯收集工具脚本

整合技能:
- tech_news      收集 Hacker News 科技资讯
- wechat         微信公众号文章搜索 (wechat-article-search)
- cn_search      中文网页搜索 (cn-web-search)
- finance        金融资讯搜索
- list           查看报告列表

使用:
python3 main.py <skill_name> [关键词]
"""
import asyncio
import aiohttp
import subprocess
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional


# ============ Hacker News 收集 ============

async def collect_hackernews(max_items: int = 10) -> List[Dict[str, Any]]:
    """收集 Hacker News 热门故事"""
    items = []

    async with aiohttp.ClientSession() as session:
        async with session.get("https://hacker-news.firebaseio.com/v0/topstories.json") as resp:
            story_ids = await resp.json()

        for story_id in story_ids[:max_items]:
            try:
                async with session.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json") as resp:
                    story = await resp.json()

                if story and story.get('url'):
                    items.append({
                        'title': story.get('title', 'Untitled'),
                        'url': story.get('url', ''),
                        'score': story.get('score', 0),
                        'author': story.get('by', 'unknown'),
                        'time': datetime.fromtimestamp(story.get('time', 0)).strftime('%Y-%m-%d %H:%M'),
                        'source': 'Hacker News'
                    })
            except Exception as e:
                print(f"Error: {e}")
                continue

    return items


# ============ 微信公众号搜索 ============

def collect_wechat_articles(keyword: str, num: int = 10) -> List[Dict[str, Any]]:
    """使用 wechat-article-search 搜索公众号文章"""
    script_path = "skills/wechat-article-search/scripts/search_wechat.js"

    if not os.path.exists(script_path):
        print(f"脚本不存在: {script_path}")
        return []

    try:
        result = subprocess.run(
            ["node", script_path, keyword, "-n", str(num)],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            print(f"搜索失败: {result.stderr}")
            return []

        # 解析 JSON 输出
        output = result.stdout.strip()

        # 找到 JSON 部分
        json_start = output.find('{')
        if json_start == -1:
            print("未找到 JSON 输出")
            return []

        json_str = output[json_start:]
        data = json.loads(json_str)

        # 提取文章列表
        articles = data.get('articles', [])
        items = []
        for article in articles:
            items.append({
                'title': article.get('title', ''),
                'url': article.get('url', ''),
                'summary': article.get('summary', ''),
                'time': article.get('datetime', ''),
                'source': article.get('source', ''),
                'account_name': article.get('source', '')
            })

        return items

    except Exception as e:
        print(f"执行错误: {e}")
        return []


# ============ 中文网页搜索 (通过 API) ============

async def collect_cn_search(keyword: str, engine: str = "baidu", num: int = 10) -> List[Dict[str, Any]]:
    """使用 cn-web-search 搜索引擎"""
    # 搜索引擎 URL 映射
    engines = {
        "baidu": f"https://www.baidu.com/s?wd={keyword}",
        "toutiao": f"https://so.toutiao.com/search?keyword={keyword}",
        "sogou_weixin": f"https://weixin.sogou.com/weixin?type=2&query={keyword}",
        "eastmoney": f"https://search.eastmoney.com/search?keyword={keyword}",
        "jisilu": f"https://www.jisilu.cn/explore/?keyword={keyword}",
        "hn": f"https://hn.algolia.com/api/v1/search?query={keyword}&tags=story&hitsPerPage={num}",
    }

    url = engines.get(engine, engines["baidu"])

    items = []

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if engine == "hn":
                    # Hacker News API 返回 JSON
                    data = await resp.json()
                    for hit in data.get('hits', [])[:num]:
                        items.append({
                            'title': hit.get('title', ''),
                            'url': hit.get('url', ''),
                            'score': hit.get('points', 0),
                            'time': datetime.fromtimestamp(hit.get('created_at_i', 0)).strftime('%Y-%m-%d %H:%M'),
                            'source': 'Hacker News Search'
                        })
                else:
                    # 其他引擎返回 HTML，需要解析（这里简化处理）
                    text = await resp.text()
                    print(f"[{engine}] 搜索完成，请使用 WebFetch 获取详细结果")
                    items.append({
                        'title': f'{engine} 搜索: {keyword}',
                        'url': url,
                        'source': engine
                    })
    except Exception as e:
        print(f"搜索错误: {e}")

    return items


# ============ 金融资讯收集 ============

async def collect_finance(keyword: str = "A股", num: int = 10) -> List[Dict[str, Any]]:
    """收集金融资讯"""
    items = []

    # 东方财富搜索
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://search.eastmoney.com/search?keyword={keyword}") as resp:
                items.append({
                    'title': f'东方财富搜索: {keyword}',
                    'url': f"https://search.eastmoney.com/search?keyword={keyword}",
                    'source': '东方财富'
                })
    except Exception as e:
        print(f"东方财富搜索错误: {e}")

    return items


# ============ 报告生成 ============

def generate_markdown_report(title: str, items: List[Dict], skill_name: str) -> str:
    """生成 Markdown 报告"""
    date_str = datetime.now().strftime('%Y-%m-%d')
    time_str = datetime.now().strftime('%H:%M:%S')

    lines = [
        f"# {title} - {date_str}",
        "",
        f"生成时间: {date_str} {time_str}",
        f"收集条目: {len(items)} 条",
        "",
        "---",
        ""
    ]

    for idx, item in enumerate(items, 1):
        title_text = item.get('title', 'Untitled')
        url = item.get('url', '#')
        source = item.get('source', 'Unknown')

        lines.append(f"{idx}. **{title_text}**")

        if url and url != '#':
            lines.append(f"   - 链接: [{url}]({url})")

        if item.get('score'):
            lines.append(f"   - 分数: {item['score']}")

        if item.get('author'):
            lines.append(f"   - 作者: {item['author']}")

        if item.get('time'):
            lines.append(f"   - 时间: {item['time']}")

        if item.get('summary'):
            lines.append(f"   - 概要: {item['summary'][:100]}...")

        if item.get('account_name'):
            lines.append(f"   - 公众号: {item['account_name']}")

        lines.append(f"   - 来源: {source}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"Skill: {skill_name}")

    return '\n'.join(lines)


def save_report(content: str, filename: str, output_dir: str = "output/reports") -> str:
    """保存报告到文件"""
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    return filepath


# ============ 任务运行 ============

async def run_tech_news():
    """运行科技资讯收集"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 收集 Hacker News 热门故事...")

    items = await collect_hackernews(10)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 收集完成: {len(items)} 条")

    content = generate_markdown_report("科技资讯日报", items, "tech_news")
    filename = f"tech_news-{datetime.now().strftime('%Y-%m-%d')}.md"

    filepath = save_report(content, filename)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 报告已保存: {filepath}")

    return filepath, items


def run_wechat_search(keyword: str, num: int = 10):
    """运行微信公众号搜索"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 搜索微信公众号: {keyword}")

    items = collect_wechat_articles(keyword, num)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 搜索完成: {len(items)} 条")

    content = generate_markdown_report(f"微信公众号搜索: {keyword}", items, "wechat")
    filename = f"wechat-{keyword}-{datetime.now().strftime('%Y-%m-%d')}.md"

    filepath = save_report(content, filename)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 报告已保存: {filepath}")

    return filepath, items


async def run_cn_search(keyword: str, engine: str = "hn", num: int = 10):
    """运行中文网页搜索"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {engine} 搜索: {keyword}")

    items = await collect_cn_search(keyword, engine, num)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 搜索完成: {len(items)} 条")

    content = generate_markdown_report(f"{engine} 搜索: {keyword}", items, "cn_search")
    filename = f"{engine}-{keyword}-{datetime.now().strftime('%Y-%m-%d')}.md"

    filepath = save_report(content, filename)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 报告已保存: {filepath}")

    return filepath, items


async def run_finance(keyword: str = "A股"):
    """运行金融资讯收集"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 收集金融资讯: {keyword}")

    items = await collect_finance(keyword)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 收集完成: {len(items)} 条")

    content = generate_markdown_report(f"金融资讯: {keyword}", items, "finance")
    filename = f"finance-{keyword}-{datetime.now().strftime('%Y-%m-%d')}.md"

    filepath = save_report(content, filename)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 报告已保存: {filepath}")

    return filepath, items


def list_reports(output_dir: str = "output/reports") -> List[str]:
    """列出所有报告"""
    if not os.path.exists(output_dir):
        return []

    files = sorted(os.listdir(output_dir), reverse=True)
    return [f for f in files if f.endswith('.md')]


# ============ 主入口 ============

async def main(skill_name: str = "tech_news", keyword: str = None):
    """主入口"""
    if skill_name == "tech_news":
        return await run_tech_news()

    elif skill_name == "wechat":
        if not keyword:
            keyword = "AI"
        return run_wechat_search(keyword)

    elif skill_name == "cn_search":
        if not keyword:
            keyword = "人工智能"
        return await run_cn_search(keyword)

    elif skill_name == "finance":
        if not keyword:
            keyword = "A股"
        return await run_finance(keyword)

    elif skill_name == "finance_news":
        # 财政系统新闻搜索
        return run_finance_news_search()

    elif skill_name == "list":
        reports = list_reports()
        print(f"已有报告: {len(reports)} 个")
        for f in reports[:10]:
            print(f"  - {f}")
        return reports

    else:
        print(f"未知 skill: {skill_name}")
        print("可用: tech_news, wechat, cn_search, finance, finance_news, list")
        return None


def run_finance_news_search():
    """运行财政系统新闻搜索"""
    import subprocess

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始搜索财政系统新闻...")

    script_path = "skills/finance-system-news-search/search.sh"
    if not os.path.exists(script_path):
        print(f"脚本不存在: {script_path}")
        return None

    result = subprocess.run(
        ["bash", script_path],
        capture_output=True,
        text=True,
        timeout=300
    )

    print(result.stdout)
    if result.stderr:
        print(f"错误: {result.stderr}")

    return result.returncode == 0


if __name__ == "__main__":
    import sys
    skill = sys.argv[1] if len(sys.argv) > 1 else "tech_news"
    keyword = sys.argv[2] if len(sys.argv) > 2 else None
    asyncio.run(main(skill, keyword))