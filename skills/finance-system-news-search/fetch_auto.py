#!/usr/bin/env python3
"""
微信公众号文章全文爬取脚本 v2.0
通过搜索引擎搜索文章标题，找到微信文章链接后爬取全文
"""

import json
import os
import sys
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

TEMP_DIR = "output/temp"


def search_wechat_url_by_title(title):
    """通过文章标题搜索微信文章URL"""
    # 清理标题中的特殊字符
    clean_title = title.replace('✓', '').replace('○', '').strip()

    # 方案1: 使用必应搜索
    try:
        query = quote(f'"{clean_title[:50]}" site:mp.weixin.qq.com')
        url = f"https://cn.bing.com/search?q={query}"
        resp = requests.get(url, headers=HEADERS, timeout=15)

        soup = BeautifulSoup(resp.text, 'html.parser')
        for item in soup.select('.b_algo h2 a'):
            href = item.get('href', '')
            if 'mp.weixin.qq.com' in href:
                return href
            # 处理 Bing 重定向链接
            if '/link?' in href:
                # 尝试从链接中提取真实URL
                if 'url=' in href:
                    from urllib.parse import unquote
                    real_url = unquote(href.split('url=')[1].split('&')[0])
                    if 'mp.weixin.qq.com' in real_url:
                        return real_url
    except Exception as e:
        print(f"    Bing搜索失败: {str(e)[:30]}")

    # 方案2: 使用搜狗微信搜索（获取搜索结果列表）
    try:
        query = quote(clean_title[:40])
        url = f"https://weixin.sogou.com/weixin?type=2&query={query}"
        resp = requests.get(url, headers=HEADERS, timeout=15)

        soup = BeautifulSoup(resp.text, 'html.parser')
        for item in soup.select('.news-list li'):
            title_elem = item.select_one('.txt-box h3 a')
            if title_elem:
                item_title = title_elem.get_text(strip=True)
                # 检查标题是否匹配
                if clean_title[:20] in item_title or item_title[:20] in clean_title:
                    link = title_elem.get('href', '')
                    if link.startswith('http'):
                        return link
    except Exception as e:
        print(f"    搜狗搜索失败: {str(e)[:30]}")

    return None


def fetch_wechat_content(url):
    """爬取微信公众号文章全文"""
    if not url or 'mp.weixin.qq.com' not in url:
        return None

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, 'html.parser')

        # 提取正文
        content_elem = soup.select_one('#js_content') or soup.select_one('.rich_media_content')
        if content_elem:
            # 清理
            for tag in content_elem.find_all(['script', 'style', 'iframe', 'svg']):
                tag.decompose()

            # 提取段落
            paragraphs = []
            for p in content_elem.find_all(['p', 'section']):
                text = p.get_text(strip=True)
                if text and len(text) > 3:
                    paragraphs.append(text)

            content = '\n\n'.join(paragraphs)
            return content if len(content) > 50 else None

    except Exception as e:
        print(f"    爬取失败: {str(e)[:30]}")

    return None


def batch_fetch(limit=10):
    """批量爬取文章全文"""
    json_file = os.path.join(TEMP_DIR, "finance-pilot-articles.json")

    if not os.path.exists(json_file):
        print(f"错误: 找不到数据文件 {json_file}")
        print("请先运行: python3 skills/finance-system-news-search/search.py")
        return

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    articles = data.get('articles', [])

    # 找出未爬取全文的文章
    to_fetch = [(i, a) for i, a in enumerate(articles) if not a.get('content')]

    if not to_fetch:
        print("所有文章都已爬取全文")
        return

    print(f"待爬取文章: {len(to_fetch)} 篇")
    print(f"本次爬取: {min(limit, len(to_fetch))} 篇\n")

    success_count = 0
    for count, (idx, article) in enumerate(to_fetch[:limit], 1):
        title = article.get('title', '')[:50]
        print(f"[{count}/{min(limit, len(to_fetch))}] {title}...")

        # 1. 搜索微信文章URL
        print("    搜索文章链接...")
        wechat_url = search_wechat_url_by_title(article.get('title', ''))

        if wechat_url:
            print(f"    找到链接: {wechat_url[:50]}...")

            # 2. 爬取全文
            content = fetch_wechat_content(wechat_url)

            if content:
                articles[idx]['content'] = content
                articles[idx]['wechat_url'] = wechat_url
                print(f"    ✓ 成功: {len(content)} 字")
                success_count += 1
            else:
                print("    ✗ 爬取内容失败")
        else:
            print("    ✗ 未找到微信链接")

        time.sleep(1)  # 避免请求过快

    # 保存
    data['articles'] = articles
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n爬取完成: {success_count}/{min(limit, len(to_fetch))} 篇成功")

    if success_count > 0:
        print("\n重新生成报告...")
        os.system("python3 skills/finance-system-news-search/generate_report.py")


def main():
    if len(sys.argv) < 2:
        print("微信公众号文章全文自动爬取")
        print("")
        print("用法:")
        print("  python3 fetch_auto.py batch [数量]    # 批量爬取（默认10篇）")
        print("  python3 fetch_auto.py test            # 测试爬取第一篇")
        print("")
        print("原理: 通过搜索引擎搜索文章标题，找到微信文章链接后爬取全文")
        return

    command = sys.argv[1]

    if command == "batch":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        batch_fetch(limit)
    elif command == "test":
        batch_fetch(limit=1)
    else:
        print(f"未知命令: {command}")


if __name__ == "__main__":
    main()