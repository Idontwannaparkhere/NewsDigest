#!/usr/bin/env node
/**
 * 微信公众号文章搜索脚本
 * 通过搜狗微信搜索获取文章列表
 * 使用: node search_wechat.js "关键词" -n 10 -o output.json -r
 */

const https = require('https');
const http = require('http');
const fs = require('fs');
const cheerio = require('cheerio');

// 解析命令行参数
function parseArgs() {
  const args = process.argv.slice(2);
  const params = {
    query: '',
    num: 10,
    output: null,
    resolveUrl: false
  };

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '-n' || args[i] === '--num') {
      params.num = parseInt(args[++i]) || 10;
    } else if (args[i] === '-o' || args[i] === '--output') {
      params.output = args[++i];
    } else if (args[i] === '-r' || args[i] === '--resolve-url') {
      params.resolveUrl = true;
    } else if (!args[i].startsWith('-')) {
      params.query = args[i];
    }
  }

  return params;
}

// 发送 HTTPS 请求
function fetch(url) {
  return new Promise((resolve, reject) => {
    const client = url.startsWith('https') ? https : http;
    const req = client.get(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
      },
      timeout: 15000
    }, (res) => {
      if (res.statusCode === 302 || res.statusCode === 301) {
        const redirectUrl = res.headers.location;
        fetch(redirectUrl).then(resolve).catch(reject);
        return;
      }

      let data = '';
      res.setEncoding('utf-8');
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve(data));
    });

    req.on('error', reject);
    req.on('timeout', () => {
      req.destroy();
      reject(new Error('Request timeout'));
    });
  });
}

// 解析真实 URL (从搜狗中间链接)
async function resolveRealUrl(sogouUrl) {
  try {
    const html = await fetch(sogouUrl);
    // 查找 mp.weixin.qq.com 链接
    const match = html.match(/url\s*=\s*['"]([^'"]*(?:mp\.weixin\.qq\.com)[^'"]*)['"]/);
    if (match) {
      return match[1];
    }

    // 另一种匹配方式
    const match2 = html.match(/var\s+url\s*=\s*['"]([^'"]+)['"]/);
    if (match2 && match2[1].includes('mp.weixin.qq.com')) {
      return match2[1];
    }

    return sogouUrl;
  } catch (e) {
    return sogouUrl;
  }
}

// 解析搜索结果页面
function parseSearchResults(html) {
  const $ = cheerio.load(html);
  const articles = [];

  $('.news-box .news-list li').each((i, el) => {
    if (articles.length >= 50) return;

    const $el = $(el);
    const $title = $el.find('.txt-box h3 a');
    const $summary = $el.find('.txt-box p');
    const $source = $el.find('.s-p .account');
    const $time = $el.find('.s-p .s2');
    const $link = $el.find('.txt-box h3 a');

    const title = $title.text().trim();
    const url = $link.attr('href') || '';
    const summary = $summary.text().trim();
    let source = $source.text().trim() || $el.find('.s-p a').first().text().trim();
    const datetimeRaw = $time.text().trim() || $time.html() || '';

    // 解析日期时间
    let datetime = datetimeRaw;
    if (datetimeRaw.includes('timeConvert')) {
      // 提取时间戳
      const match = datetimeRaw.match(/timeConvert\('(\d+)'\)/);
      if (match) {
        const timestamp = parseInt(match[1]);
        const date = new Date(timestamp * 1000);
        datetime = date.toISOString().slice(0, 19).replace('T', ' ');
      }
    }

    if (title && url) {
      articles.push({
        title,
        url,
        summary: summary.replace(/\n/g, ' ').trim(),
        source,
        datetime
      });
    }
  });

  return articles;
}

// 格式化日期时间
function formatDateTime(datetimeStr) {
  // 常见格式: "2026-03-28 10:00", "3天前", "昨天"
  if (datetimeStr.includes('前') || datetimeStr.includes('天')) {
    const now = new Date();
    if (datetimeStr.includes('昨天')) {
      now.setDate(now.getDate() - 1);
      return now.toISOString().slice(0, 10) + ' 00:00:00';
    }
    const match = datetimeStr.match(/(\d+)\s*天前/);
    if (match) {
      now.setDate(now.getDate() - parseInt(match[1]));
      return now.toISOString().slice(0, 10) + ' 00:00:00';
    }
    return new Date().toISOString().slice(0, 10) + ' 00:00:00';
  }
  return datetimeStr;
}

// 主函数
async function main() {
  const params = parseArgs();

  if (!params.query) {
    console.error('请提供搜索关键词');
    console.error('用法: node search_wechat.js "关键词" [-n 数量] [-o 输出文件] [-r]');
    process.exit(1);
  }

  console.log(`搜索: ${params.query}`);

  const encodedQuery = encodeURIComponent(params.query);
  const searchUrl = `https://weixin.sogou.com/weixin?type=2&query=${encodedQuery}&w=${params.query.split(' ')[0]}`;

  try {
    const html = await fetch(searchUrl);
    let articles = parseSearchResults(html);

    // 格式化日期
    articles = articles.map(a => ({
      ...a,
      datetime: formatDateTime(a.datetime)
    }));

    // 解析真实 URL
    if (params.resolveUrl) {
      console.log('解析真实链接...');
      const resolvePromises = articles.slice(0, params.num).map(async a => {
        if (a.url.includes('weixin.sogou.com')) {
          const realUrl = await resolveRealUrl(a.url);
          return { ...a, url: realUrl };
        }
        return a;
      });

      articles = await Promise.all(resolvePromises);
    }

    // 限制数量
    articles = articles.slice(0, params.num);

    console.log(`找到 ${articles.length} 条结果`);

    // 输出结果
    const result = {
      query: params.query,
      total: articles.length,
      articles
    };

    if (params.output) {
      fs.writeFileSync(params.output, JSON.stringify(result, null, 2));
      console.log(`已保存到: ${params.output}`);
    } else {
      console.log(JSON.stringify(result, null, 2));
    }

  } catch (error) {
    console.error('搜索失败:', error.message);

    // 返回空结果而不是报错
    const emptyResult = {
      query: params.query,
      total: 0,
      articles: []
    };

    if (params.output) {
      fs.writeFileSync(params.output, JSON.stringify(emptyResult, null, 2));
    } else {
      console.log(JSON.stringify(emptyResult, null, 2));
    }
  }
}

main();