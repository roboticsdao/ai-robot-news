#!/usr/bin/env python3
import os, subprocess, re, sys, time
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

CSS = """
:root{--bg:#fff;--fg:#1a1a1a;--fg2:#6b6b6f;--fg3:#9a9a9e;--border:#d4d4d4;--border2:#e8e8e8;--serif:Georgia,"Times New Roman",serif;--sans:-apple-system,BlinkMacSystemFont,"Helvetica Neue",sans-serif;--link:#1a6ed8}
@media(prefers-color-scheme:dark){:root{--bg:#1a1a1a;--fg:#e2e2e2;--fg2:#a0a0a0;--fg3:#707070;--border:#444;--border2:#333;--link:#6db3f8}}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:var(--sans);margin:0 auto;padding:28px 24px;background:var(--bg);color:var(--fg);line-height:1.75;font-size:15px;-webkit-font-smoothing:antialiased;max-width:780px}
@media(max-width:600px){body{padding:20px 16px}}
.masthead{padding:0 0 14px;border-bottom:3px double var(--border);margin-bottom:20px}
.masthead h1{font-family:var(--serif);font-size:22px;font-weight:700;letter-spacing:-0.5px}
.masthead .date{font-size:12px;color:var(--fg3);margin-top:3px}
.disclaimer{font-size:12px;color:var(--fg3);font-style:italic;margin-bottom:22px;padding-bottom:14px;border-bottom:0.5px solid var(--border2)}
.region{margin-bottom:32px}
.region-head{font-family:var(--serif);font-size:16px;font-weight:700;padding:4px 0 8px;border-bottom:1.5px solid var(--border);margin-bottom:12px}
.item{padding:10px 0 12px;border-bottom:0.5px solid var(--border2)}
.item:last-child{border-bottom:none}
.item-date{font-size:11px;color:var(--fg3)}
.item-title{font-family:var(--serif);font-size:15px;font-weight:700;margin:2px 0 5px;line-height:1.5}
.item-en{font-size:13px;color:var(--fg2);line-height:1.6;margin:0 0 2px}
.item-zh{font-size:13px;line-height:1.6;margin:0 0 6px}
.item-src{font-size:12px;font-style:italic;color:var(--fg3)}
.item-src a{color:var(--link);text-decoration:none;border-bottom:0.5px solid transparent}
.item-src a:hover{border-bottom-color:var(--link)}
.footer{margin-top:32px;padding-top:14px;border-top:3px double var(--border);font-size:11px;color:var(--fg3);text-align:center}
"""

REGIONS = [
    ("🇺🇸", "美国 / United States", "US AI robotics humanoid robot Tesla Optimus Figure Boston Dynamics"),
    ("🇨🇳", "中国 / China", "China AI robotics humanoid robot 中国 机器人 人形 Unitree 宇树 小鹏 优必选"),
    ("🇯🇵", "日本 / Japan", "Japan AI robotics humanoid robot 日本 ロボット Honda Fanuc Telexistence Toyota"),
]

def call_gemini(prompt, use_search=True):
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=GEMINI_API_KEY)
    config_args = {"temperature": 0.3}
    if use_search:
        config_args["tools"] = [types.Tool(google_search=types.GoogleSearch())]
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(**config_args),
    )
    return response.text or ""

def fetch_region(flag, label, keywords):
    prompt = f"""Search for 3 to 5 recent AI robotics news specifically from {label}.
Search keywords: {keywords}
Today is {DATE_STR}.

CRITICAL RULES:
- You MUST return 3-5 news items. NEVER return zero.
- Prioritize last 24 hours, then expand to 2 weeks if needed.
- NEVER say "sorry", "unable to find", "无法获取". This is FORBIDDEN.
- Each item MUST start with: - **[date] Company — Chinese summary**
- Source URL: use direct article URLs (https://reuters.com/..., https://techcrunch.com/...). If you only have a Google redirect URL, use the source publication's homepage instead (e.g. https://www.reuters.com, https://techcrunch.com).
- NEVER use vertexaisearch.cloud.google.com URLs.

FORMAT (exactly this, pure Markdown):

- **[2026.06.19] Company — 中文事件概要**
  English: One-line English summary of the news.
  中文：一行中文摘要。
  📰 [Source Name](https://direct-article-url)

- **[2026.06.18] Another Company — 另一个事件概要**
  English: Summary.
  中文：摘要。
  📰 [Source Name](https://direct-url)

(produce 3-5 items)"""

    for attempt in range(3):
        try:
            text = call_gemini(prompt, use_search=True)
            # Clean Google redirect URLs
            text = re.sub(r'https://vertexaisearch\.cloud\.google\.com/[^\s\)]+', 'https://www.google.com/search?q=' + keywords.split()[0], text)
            if "- **" in text and "很抱歉" not in text and "无法获取" not in text:
                print(f"   {flag} Got {text.count('- **')} items (attempt {attempt+1})")
                return text
            print(f"   {flag} Attempt {attempt+1}: insufficient content")
        except Exception as e:
            print(f"   {flag} Attempt {attempt+1} error: {e}")
        time.sleep(3)

    # Fallback without search
    print(f"   {flag} Using training data fallback...")
    fallback = f"""Based on your training knowledge, list 3 recent AI robotics news items from {label}.
Use real companies and real events. Pick the most recent you know about.
You MUST produce exactly 3 items. NEVER say sorry or unable.
Format each exactly as:
- **[approximate date] Company — 中文概要**
  English: summary
  中文：摘要
  📰 [Source](https://company-or-publication-homepage)"""
    try:
        text = call_gemini(fallback, use_search=False)
        if "- **" in text:
            return text
    except Exception as e:
        print(f"   {flag} Fallback error: {e}")
    return ""

def generate_digest():
    header = f"""# 🤖 AI Robot News | {DATE_STR}（{WEEKDAY_JP}曜日 / {WEEKDAY_EN}）

> ⚠️ 本日报优先收录24小时内新闻，不足部分回溯至近两周。

---
"""
    parts = [header]
    for flag, label, keywords in REGIONS:
        print(f"\n   Fetching {flag} {label}...")
        region_content = fetch_region(flag, label, keywords)
        parts.append(f"\n## {flag} {label}\n")
        if region_content:
            parts.append(region_content)
        else:
            parts.append("- **[" + DATE_STR + "] 暂无更新 — No updates available**\n  English: No recent news found for this region.\n  中文：该地区暂无最新新闻。")
        time.sleep(2)

    parts.append(f"\n---\n※AI Robot News Digest | {DATE_STR}")
    return "\n".join(parts)

def linkify(text):
    text = re.sub(r'\[([^\]]+)\]\((https?://[^\)]+)\)',
        lambda m: '<a href="'+m.group(2)+'" target="_blank">'+m.group(1)+' ↗</a>', text)
    text = re.sub(r'<(https?://[^>]+)>',
        lambda m: '<a href="'+m.group(1)+'" target="_blank">'+re.sub(r'https?://(www\.)?','',m.group(1)).split('/')[0]+' ↗</a>', text)
    text = re.sub(r'(?<!href=")(https?://[^\s<>"\')\],]+)',
        lambda m: '<a href="'+m.group(1)+'" target="_blank">'+re.sub(r'https?://(www\.)?','',m.group(1)).split('/')[0]+' ↗</a>', text)
    return text

def md_to_html(md):
    regions = []
    current_region = None
    current_items = []
    disclaimer = ""

    for line in md.split("\n"):
        s = line.strip()
        if s.startswith("> "):
            disclaimer = s[2:].strip()
        elif s.startswith("## "):
            if current_region and current_items:
                regions.append((current_region, current_items))
            heading = s[3:].strip()
            flag = ""
            if "🇺🇸" in heading: flag = "🇺🇸"
            elif "🇨🇳" in heading: flag = "🇨🇳"
            elif "🇯🇵" in heading: flag = "🇯🇵"
            label = re.sub(r'[🇺🇸🇨🇳🇯🇵]\s*', '', heading).strip()
            current_region = (flag, label)
            current_items = []
        elif s.startswith("- **"):
            match = re.match(r'-\s*\*\*\[?([^\]]+?)\]?\s*(.+?)\*\*', s)
            if match:
                current_items.append({"date": match.group(1).strip(), "title": match.group(2).lstrip("] ").strip(), "lines": []})
            else:
                title = re.sub(r'^\-\s*\*\*(.+?)\*\*.*', r'\1', s)
                current_items.append({"date": "", "title": title, "lines": []})
        elif current_items and not s.startswith("## ") and not s.startswith("# ") and not s.startswith("---") and s:
            current_items[-1]["lines"].append(s)

    if current_region and current_items:
        regions.append((current_region, current_items))

    parts = []
    for (flag, label), items in regions:
        parts.append(f'<div class="region"><div class="region-head">{flag} {label}</div>')
        for it in items:
            en_line = zh_line = src_html = ""
            for ln in it["lines"]:
                if ln.startswith("📰"):
                    ln_linked = linkify(ln.replace("📰", "").strip())
                    src_html = f'<div class="item-src">📰 {ln_linked}</div>'
                elif ln.lower().startswith("english:") or ln.lower().startswith("en:"):
                    en_line = ln.split(":", 1)[1].strip()
                elif "中文" in ln[:4]:
                    zh_line = re.split(r'[：:]', ln, 1)[-1].strip()
                elif not en_line and not any('\u4e00' <= c <= '\u9fff' for c in ln[:10]):
                    en_line = ln
                elif not zh_line:
                    zh_line = ln
            en_html = f'<p class="item-en">{en_line}</p>' if en_line else ""
            zh_html = f'<p class="item-zh">{zh_line}</p>' if zh_line else ""
            parts.append(f'<div class="item"><div class="item-date">{it["date"]}</div><div class="item-title">{it["title"]}</div>{en_html}{zh_html}{src_html}</div>')
        parts.append('</div>')
    body = "\n".join(parts)

    if not disclaimer:
        disclaimer = "⚠ 本日报优先收录24小时内新闻，不足部分回溯至近两周。"

    return f'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Robot News | {DATE_STR}</title>
<style>{CSS}</style>
</head>
<body>
<div class="masthead"><h1>AI Robot News</h1><div class="date">{DATE_STR} — {WEEKDAY_EN} / {WEEKDAY_JP}曜日</div></div>
<div class="disclaimer">{disclaimer}</div>
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
    result = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if result.returncode != 0:
        subprocess.run(["git", "commit", "-m", f"update {DATE_STR}"], check=True)
        subprocess.run(["git", "push"], check=True)
        print(f"   ✅ Published: {PAGE_URL}")
    else:
        print("   No changes to push")

if __name__ == "__main__":
    print(f"🤖 AI Robot News — {DATE_STR} ({WEEKDAY_JP})")
    print("=" * 50)
    print("\n📝 Generating digest (region by region)...")
    digest = generate_digest()
    if not digest or digest.count("- **") < 3:
        print("❌ Failed to generate enough content")
        sys.exit(1)
    OUTPUT_FILE.write_text(digest, encoding="utf-8")
    print(f"\n   Total items: {digest.count('- **')}")
    print(f"   Saved: {OUTPUT_FILE}")
    print("\n🌐 Publishing...")
    try:
        push_to_github(md_to_html(digest))
    except Exception as e:
        print(f"   ❌ GitHub: {e}")
    print("\n✅ Done!")
