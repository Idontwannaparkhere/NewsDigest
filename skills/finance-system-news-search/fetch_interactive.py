#!/usr/bin/env python3
"""
微信公众号文章全文爬取脚本 - 可视化版
打开浏览器窗口，用户可以看到操作过程并手动处理验证码
"""

import json
import os
import sys
import time
from bs4 import BeautifulSoup

TEMP_DIR = "output/temp"


def fetch_with_browser(sogou_link):
    """使用带界面的浏览器打开链接"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
    except ImportError:
        print("请先安装 selenium: pip install selenium")
        return None

    options = Options()
    # 不使用无头模式，显示浏览器窗口
    options.add_argument('--start-maximized')
    options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    try:
        driver = webdriver.Chrome(options=options)

        # 打开搜狗链接
        full_url = f"https://weixin.sogou.com{sogou_link}"
        print(f"\n打开浏览器访问: {full_url[:60]}...")
        print("\n请在浏览器窗口中操作:")
        print("1. 如有验证码，请手动完成验证")
        print("2. 点击搜索结果中的文章链接")
        print("3. 等待微信文章页面加载完成")
        print("4. 按 Enter 键继续爬取内容...")
        driver.get(full_url)

        # 等待用户操作
        input("\n完成上述步骤后，按 Enter 继续...")

        # 检查当前URL
        current_url = driver.current_url
        print(f"当前页面: {current_url[:60]}...")

        if 'mp.weixin.qq.com' in current_url:
            # 提取内容
            result = extract_content_from_driver(driver)
            driver.quit()
            return result
        else:
            print("当前不在微信文章页面，无法爬取")
            driver.quit()
            return None

    except Exception as e:
        print(f"错误: {e}")
        return None


def extract_content_from_driver(driver):
    """从浏览器页面提取内容"""
    try:
        # 提取标题
        try:
            title = driver.find_element(By.ID, 'activity-name').text
        except:
            title = driver.title

        # 提取正文
        content_elem = driver.find_element(By.ID, 'js_content')
        content_html = content_elem.get_attribute('innerHTML')

        soup = BeautifulSoup(content_html, 'html.parser')
        for tag in soup.find_all(['script', 'style', 'iframe', 'svg']):
            tag.decompose()

        paragraphs = []
        for p in soup.find_all(['p', 'section']):
            text = p.get_text(strip=True)
            if text and len(text) > 3:
                paragraphs.append(text)

        content = '\n\n'.join(paragraphs)

        return {
            'title': title,
            'url': driver.current_url,
            'content': content,
            'content_length': len(content)
        }
    except Exception as e:
        print(f"提取内容失败: {e}")
        return None


def interactive_fetch(article_index=None):
    """交互式爬取"""
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

    if article_index is None:
        # 显示文章列表让用户选择
        print("\n待爬取的文章:\n")
        for i, (idx, article) in enumerate(to_fetch[:20], 1):
            title = article.get('title', '')[:50]
            print(f"{i:2}. {title}...")

        print(f"\n共 {len(to_fetch)} 篇文章待爬取")
        choice = input("\n请输入要爬取的文章序号（1-20），或按 Enter 爬取第一篇: ").strip()
        article_index = int(choice) if choice else 1

    if article_index < 1 or article_index > len(to_fetch):
        print(f"序号应在 1-{len(to_fetch)} 之间")
        return

    idx, article = to_fetch[article_index - 1]
    title = article.get('title', '')
    print(f"\n准备爬取: {title[:50]}...")

    result = fetch_with_browser(article.get('url', ''))

    if result:
        articles[idx]['content'] = result['content']
        articles[idx]['wechat_url'] = result['url']

        data['articles'] = articles
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n✓ 成功爬取 {result['content_length']} 字")
        print(f"已保存到: {json_file}")

        # 重新生成报告
        print("\n重新生成报告...")
        os.system("python3 skills/finance-system-news-search/generate_report.py")
    else:
        print("\n✗ 爬取失败")


def main():
    print("微信公众号文章全文爬取 - 可视化版")
    print("=" * 50)
    print("此脚本会打开浏览器窗口，让你可以看到操作过程")
    print("遇到验证码时可以手动处理")
    print("=" * 50)

    if len(sys.argv) > 1:
        index = int(sys.argv[1])
        interactive_fetch(index)
    else:
        interactive_fetch()


if __name__ == "__main__":
    main()