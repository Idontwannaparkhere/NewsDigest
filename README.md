# NewsDigest - 资讯收集与报告生成工具

整合 SkillHub 技能的资讯收集工具，支持多种资讯来源。

## 已安装的技能

| Skill | 来源 | 说明 |
|-------|------|------|
| `tech_news` | Hacker News API | 科技资讯热门故事 |
| `wechat` | wechat-article-search | 微信公众号文章搜索 |
| `cn_search` | cn-web-search | 中文网页搜索 (22+ 引擎) |
| `finance` | 东方财富等 | 金融资讯收集 |
| `list` | 本地 | 查看已生成报告 |

## 使用方式

### 命令行运行

```bash
# 科技资讯 (Hacker News)
python3 main.py tech_news

# 微信公众号搜索
python3 main.py wechat "人工智能"
python3 main.py wechat "AI技术"

# 中文网页搜索 (Hacker News API)
python3 main.py cn_search "AI"

# 金融资讯
python3 main.py finance "A股"
python3 main.py finance "人工智能"

# 查看报告列表
python3 main.py list
```

### 定时任务 (CronCreate)

```javascript
// 每天 9:00 收集科技资讯
CronCreate({
  "cron": "0 9 * * *",
  "prompt": "运行 python3 /Users/whl/Desktop/Projects/NewsDigest/main.py tech_news",
  "recurring": true,
  "durable": true
})

// 每天 8:00 收集微信公众号文章
CronCreate({
  "cron": "0 8 * * *",
  "prompt": "运行 python3 /Users/whl/Desktop/Projects/NewsDigest/main.py wechat 人工智能",
  "recurring": true,
  "durable": true
})
```

## 已生成的报告

| 报告 | 内容 |
|------|------|
| `tech_news-2026-04-01.md` | Hacker News 10条热门故事 |
| `wechat-人工智能-2026-04-01.md` | 微信公众号"人工智能"相关文章 |
| `hn-AI-2026-04-01.md` | Hacker News "AI" 搜索结果 |

## cn-web-search 支持的引擎

| 类别 | 引擎 |
|------|------|
| 公众号 | 搜狗微信、必应索引 |
| 中文综合 | 百度、360、搜狗、头条搜索 |
| 英文综合 | Brave、DuckDuckGo、Yahoo、Mojeek |
| 技术 | Stack Overflow、GitHub、Hacker News |
| 学术 | ArXiv |
| 财经 | 东方财富、集思录、财新 |
| 知识 | Wikipedia、Wolfram Alpha |

## 项目结构

```
NewsDigest/
├── main.py                    # 主入口脚本
├── skills/                    # 已安装技能
│   ├── clawdhub/             # ClawdHub CLI
│   ├── cn-web-search/        # 中文网页搜索
│   └── wechat-article-search/ # 微信公众号搜索
├── output/reports/            # 生成的报告
└── config/                    # 配置文件
```