#!/usr/bin/env python3
"""
微信公众号文章全文爬取脚本
需要提供真实的微信文章URL (mp.weixin.qq.com开头)
"""

import requests
import json
import os
import sys
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

TEMP_DIR = "output/temp"


def fetch_wechat_content(url):
    """爬取微信公众号文章全文"""
    if not url or 'mp.weixin.qq.com' not in url:
        print("错误: 需要提供 mp.weixin.qq.com 开头的真实URL")
        return None

    try:
        print(f"正在爬取: {url}")
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, 'html.parser')

        # 提取标题
        title_elem = soup.select_one('#activity-name') or soup.select_one('.rich_media_title')
        title = title_elem.get_text(strip=True) if title_elem else '未知标题'
        print(f"标题: {title}")

        # 提取作者/公众号
        author_elem = soup.select_one('#js_name') or soup.select_one('.rich_media_meta_nickname')
        author = author_elem.get_text(strip=True) if author_elem else ''

        # 提取正文
        content_elem = soup.select_one('#js_content') or soup.select_one('.rich_media_content')
        if content_elem:
            # 清理不需要的元素
            for tag in content_elem.find_all(['script', 'style', 'iframe', 'svg']):
                tag.decompose()

            # 提取段落
            paragraphs = []
            for p in content_elem.find_all(['p', 'section']):
                text = p.get_text(strip=True)
                if text and len(text) > 3:
                    paragraphs.append(text)

            content = '\n\n'.join(paragraphs)

            return {
                'title': title,
                'author': author,
                'url': url,
                'content': content,
                'content_length': len(content)
            }

        return None

    except Exception as e:
        print(f"爬取失败: {e}")
        return None


def update_article_content(article_index, wechat_url):
    """更新文章的全文内容"""
    json_file = os.path.join(TEMP_DIR, "finance-pilot-articles.json")

    if not os.path.exists(json_file):
        print(f"错误: 找不到数据文件 {json_file}")
        return False

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    articles = data.get('articles', [])

    if article_index < 1 or article_index > len(articles):
        print(f"错误: 文章索引应在 1-{len(articles)} 之间")
        return False

    article = articles[article_index - 1]
    print(f"\n目标文章: {article.get('title', '')[:40]}...")

    # 爬取全文
    result = fetch_wechat_content(wechat_url)

    if result:
        article['content'] = result['content']
        article['wechat_url'] = wechat_url

        # 保存更新
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n成功! 爬取了 {result['content_length']} 字")
        print(f"已保存到: {json_file}")
        return True

    return False


def list_articles():
    """列出所有文章"""
    json_file = os.path.join(TEMP_DIR, "finance-pilot-articles.json")

    if not os.path.exists(json_file):
        print(f"错误: 找不到数据文件 {json_file}")
        print("请先运行 search.py 搜索文章")
        return

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    articles = data.get('articles', [])
    print(f"\n共 {len(articles)} 篇文章:\n")

    for i, article in enumerate(articles[:30], 1):  # 最多显示30篇
        title = article.get('title', '')[:40]
        has_content = "✓" if article.get('content') else "○"
        print(f"{i:2}. [{has_content}] {title}...")


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 fetch_content.py list              # 列出所有文章")
        print("  python3 fetch_content.py <序号> <微信URL>  # 爬取指定文章全文")
        print("\n示例:")
        print("  python3 fetch_content.py 1 https://mp.weixin.qq.com/s/xxxxx")
        return

    command = sys.argv[1]

    if command == "list":
        list_articles()
    elif command.isdigit():
        if len(sys.argv) < 3:
            print("错误: 需要提供微信文章URL")
            print("用法: python3 fetch_content.py <序号> <微信URL>")
            return
        article_index = int(command)
        wechat_url = sys.argv[2]
        update_article_content(article_index, wechat_url)
    else:
        print(f"未知命令: {command}")


if __name__ == "__main__":
    main()