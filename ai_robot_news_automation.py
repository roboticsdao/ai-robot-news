#!/usr/bin/env python3
import os, subprocess, re, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))
TODAY = datetime.now(JST)
DATE_STR = TODAY.strftime("%Y.%m.%d")
WEEKDAY_MAP = {0:"月",1:"火",2:"水",3:"木",4:"金",5:"土",6:"日"}
WEEKDAY_EN = TODAY.strftime("%A")
WEEKDAY_JP = WEEKDAY_MAP[TODAY.weekday()]

IS_CI = os.environ.get("CI", "") == "true"
OUTPUT_DIR = Path.cwd() if IS_CI else (Path.home() / "ai-robot-news")
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / f"AI_Robot_News_{TODAY.strftime('%Y%m%d')}.md"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
PAGE_URL = "https://roboticsdao.github.io/ai-robot-news/latest.html"

def generate_digest():
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"""You are an AI robotics news editor. Today is {DATE_STR} ({WEEKDAY_EN}).

Search for AI robotics news from US, China, and Japan.

RULES:
- 3 to 5 news per region (9-15 total). Never fewer than 3.
- Prioritize last 24h. If not enough, go back 1 week, then 2 weeks, until you have 3-5.
- Each item MUST have publication date.
- Source URL must be a DIRECT article link (https://example.com/article-title), NOT a Google/Vertex redirect. No angle brackets around URLs.

FORMAT (pure Markdown, no code fences):

# 🤖 AI Robot News | {DATE_STR}（{WEEKDAY_JP}曜日 / {WEEKDAY_EN}）

> ⚠️ 本日报优先收录24小时内新闻，不足部分回溯至近两周。

---

## 🇺🇸 美国 / United States

- **[2026.06.19] Company — 中文事件概要**
  English: One-line English summary.
  中文：一行中文摘要。
  📰 [Source Name](https://direct-url-to-article)

## 🇨🇳 中国 / China
(same format, 3-5 items)

## 🇯🇵 日本 / Japan
(same format, 3-5 items)

---
※AI Robot News Digest | {DATE_STR}"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.3,
        ),
    )
    return response.text

def md_to_html(md):
    regions = []
    current_region = None
    current_items = []
    disclaimer = ""
    
    lines = md.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith("> "):
            disclaimer = line[2:].strip()
        elif line.startswith("## "):
            if current_region and current_items:
                regions.append((current_region, current_items))
            heading = line[3:].strip()
            flag = ""
            if "🇺🇸" in heading: flag = "🇺🇸"
            elif "🇨🇳" in heading: flag = "🇨🇳"
            elif "🇯🇵" in heading: flag = "🇯🇵"
            label = re.sub(r'[🇺🇸🇨🇳🇯🇵]\s*', '', heading).strip()
            current_region = (flag, label)
            current_items = []
        elif line.startswith("- **"):
            match = re.match(r'-\s*\*\*\[?(\d{4}[\.\-/]\d{2}[\.\-/]\d{2})\]?\s*(.+?)\*\*', line)
            date_str = match.group(1) if match else ""
            title = match.group(2).lstrip("] ").strip() if match else re.sub(r'^\-\s*\*\*(.+?)\*\*.*', r'\1', line)
            item = {"date": date_str, "title": title, "en": "", "zh": "", "source": "", "url": ""}
            j = i + 1
            while j < len(lines):
                nl = lines[j].strip()
                if nl.startswith("- **") or nl.startswith("## ") or nl.startswith("---"):
                    break
                if nl.lower().startswith("english:"):
                    item["en"] = nl.split(":", 1)[1].strip()
                elif nl.lower().startswith("en:"):
                    item["en"] = nl.split(":", 1)[1].strip()
                elif nl.startswith("中文") or nl.startswith("中文：") or nl.startswith("中文:"):
                    item["zh"] = nl.split("：", 1)[-1].split(":", 1)[-1].strip()
                elif nl.startswith("📰"):
                    md_link = re.search(r'\[([^\]]+)\]\((https?://[^\)]+)\)', nl)
                    bare_url = re.search(r'(https?://[^\s<>\)]+)', nl)
                    if md_link:
                        item["source"] = md_link.group(1)
                        item["url"] = md_link.group(2)
                    elif bare_url:
                        item["url"] = bare_url.group(1)
                        src_text = nl.replace("📰", "").strip()
                        src_text = re.sub(r'https?://[^\s]+', '', src_text).strip().rstrip("|").strip()
                        item["source"] = src_text if src_text else re.sub(r'https?://(www\.)?', '', item["url"]).split("/")[0]
                    else:
                        item["source"] = nl.replace("📰", "").strip()
                elif not item["en"] and nl and not nl.startswith("#"):
                    if any(c > '\u4e00' for c in nl):
                        item["zh"] = nl
                    else:
                        item["en"] = nl
                j += 1
            current_items.append(item)
            i = j - 1
        i += 1
    
    if current_region and current_items:
        regions.append((current_region, current_items))
    
    items_html = []
    for (flag, label), items in regions:
        items_html.append(f'<div class="region">')
        items_html.append(f'<div class="region-head"><span class="flag">{flag}</span> {label}</div>')
        for it in items:
            src_display = it["source"] if it["source"] else re.sub(r'https?://(www\.)?', '', it["url"]).split("/")[0] if it["url"] else ""
            url_html = f'<a href="{it["url"]}" target="_blank">{src_display} ↗</a>' if it["url"] else src_display
            items_html.append(f'''<div class="item">
<div class="item-date">{it["date"]}</div>
<div class="item-title">{it["title"]}</div>
{"<p class='item-en'>" + it["en"] + "</p>" if it["en"] else ""}
{"<p class='item-zh'>" + it["zh"] + "</p>" if it["zh"] else ""}
<div class="item-src">📰 {url_html}</div>
</div>''')
        items_html.append('</div>')
    
    body = "\n".join(items_html)
    
    return f'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Robot News | {DATE_STR}</title>
<style>
:root{{--bg:#fff;--fg:#1a1a1a;--fg2:#6b6b6f;--fg3:#9a9a9e;--border:#d4d4d4;--border2:#e8e8e8;--src-bg:#f5f5f5;--serif:Georgia,"Times New Roman",serif;--sans:-apple-system,BlinkMacSystemFont,"Helvetica Neue",sans-serif;--link:#1a6ed8}}
@media(prefers-color-scheme:dark){{:root{{--bg:#1a1a1a;--fg:#e2e2e2;--fg2:#a0a0a0;--fg3:#707070;--border:#444;--border2:#333;--src-bg:#252525;--link:#6db3f8}}}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:var(--sans);margin:0 auto;padding:28px 24px;background:var(--bg);color:var(--fg);line-height:1.75;font-size:15px;-webkit-font-smoothing:antialiased;max-width:780px}}
@media(max-width:600px){{body{{padding:20px 16px}}}}
.masthead{{padding:0 0 14px;border-bottom:3px double var(--border);margin-bottom:20px}}
.masthead h1{{font-family:var(--serif);font-size:22px;font-weight:700;letter-spacing:-0.5px;margin:0}}
.masthead .date{{font-size:12px;color:var(--fg3);margin-top:3px;letter-spacing:0.3px}}
.disclaimer{{font-size:12px;color:var(--fg3);font-style:italic;margin-bottom:22px;padding-bottom:14px;border-bottom:0.5px solid var(--border2)}}
.region{{margin-bottom:32px}}
.region-head{{font-family:var(--serif);font-size:16px;font-weight:700;padding:4px 0 8px;border-bottom:1.5px solid var(--border);margin-bottom:12px;display:flex;align-items:center;gap:8px}}
.flag{{font-size:14px}}
.item{{padding:10px 0 12px;border-bottom:0.5px solid var(--border2)}}
.item:last-child{{border-bottom:none}}
.item-date{{font-size:11px;color:var(--fg3);font-variant-numeric:tabular-nums;letter-spacing:0.3px}}
.item-title{{font-family:var(--serif);font-size:15px;font-weight:700;margin:2px 0 5px;color:var(--fg);line-height:1.5}}
.item-en{{font-size:13px;color:var(--fg2);line-height:1.6;margin:0 0 2px}}
.item-zh{{font-size:13px;color:var(--fg);line-height:1.6;margin:0 0 6px}}
.item-src{{font-size:12px;font-style:italic;color:var(--fg3)}}
.item-src a{{color:var(--link);text-decoration:none;border-bottom:0.5px solid transparent;transition:border-color .15s}}
.item-src a:hover{{border-bottom-color:var(--link)}}
.footer{{margin-top:32px;padding-top:14px;border-top:3px double var(--border);font-size:11px;color:var(--fg3);text-align:center;letter-spacing:0.3px}}
</style>
</head>
<body>
<div class="masthead">
<h1>AI Robot News</h1>
<div class="date">{DATE_STR} — {WEEKDAY_EN} / {WEEKDAY_JP}曜日</div>
</div>
<div class="disclaimer">{disclaimer if disclaimer else "⚠ 本日报优先收录24小时内新闻，不足部分回溯至近两周。"}</div>
{body}
<div class="footer">※ AI Robot News Digest · roboticsdao.github.io</div>
</body>
</html>'''

def push_to_github(html_content):
    html_file = OUTPUT_DIR / "latest.html"
    html_file.write_text(html_content, encoding="utf-8")
    dated = OUTPUT_DIR / ("AI_Robot_News_" + TODAY.strftime("%Y%m%d") + ".html")
    dated.write_text(html_content, encoding="utf-8")
    os.chdir(str(OUTPUT_DIR))
    subprocess.run(["git", "add", "latest.html", dated.name], check=True)
    subprocess.run(["git", "commit", "-m", f"update {DATE_STR}"], check=True)
    subprocess.run(["git", "push"], check=True)
    print(f"✅ Published: {PAGE_URL}")

if __name__ == "__main__":
    print(f"🤖 AI Robot News — {DATE_STR} ({WEEKDAY_JP})")
    print("=" * 50)
    print("\n📝 Generating digest...")
    digest = generate_digest()
    OUTPUT_FILE.write_text(digest, encoding="utf-8")
    print(f"   Saved: {OUTPUT_FILE}")
    print("\n🌐 Publishing...")
    try:
        push_to_github(md_to_html(digest))
    except Exception as e:
        print(f"❌ GitHub: {e}")
    print("\n✅ Done!")
