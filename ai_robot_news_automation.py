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

def has_real_content(text):
    return "- **[" in text and text.count("- **") >= 3 and "很抱歉" not in text and "无法获取" not in text

def generate_digest():
    base_prompt = f"""You are an AI robotics news editor. Today is {DATE_STR} ({WEEKDAY_EN}).

CRITICAL INSTRUCTIONS:
- You MUST produce exactly 3-5 news items per region. NEVER output zero items.
- You MUST NEVER say "sorry", "unable to find", "无法获取", or similar. This is FORBIDDEN.
- If you cannot find news from the last 24 hours, use news from the past 2 weeks.
- If you still cannot find specific articles, reference well-known recent developments from major AI robotics companies (Tesla Optimus, Figure AI, Unitree, Boston Dynamics, FANUC, Honda, etc.)
- Source URLs: use direct links. If unsure of exact URL, use the company or publication homepage.

Search for AI robotics news from US, China, and Japan.

FORMAT (pure Markdown, no code fences):

# 🤖 AI Robot News | {DATE_STR}（{WEEKDAY_JP}曜日 / {WEEKDAY_EN}）

> ⚠️ 本日报优先收录24小时内新闻，不足部分回溯至近两周。

---

## 🇺🇸 美国 / United States

- **[{DATE_STR}] Company — 中文事件概要**
  English: One-line English summary.
  中文：一行中文摘要。
  📰 [Source Name](https://direct-url)

(3-5 items)

## 🇨🇳 中国 / China
(3-5 items, same format)

## 🇯🇵 日本 / Japan
(3-5 items, same format)

---
※AI Robot News Digest | {DATE_STR}"""

    # Attempt 1-3: with Google Search
    for attempt in range(3):
        print(f"   Attempt {attempt+1}/3 (with search)...")
        try:
            text = call_gemini(base_prompt, use_search=True)
            if has_real_content(text):
                print(f"   Got {text.count('- **')} items")
                return text
            print(f"   Insufficient content, retrying...")
        except Exception as e:
            print(f"   Error: {e}")
        time.sleep(5)

    # Attempt 4-5: search by region separately
    print("   Trying region-by-region search...")
    combined_parts = [f"# 🤖 AI Robot News | {DATE_STR}（{WEEKDAY_JP}曜日 / {WEEKDAY_EN}）\n\n> ⚠️ 本日报优先收录24小时内新闻，不足部分回溯至近两周。\n\n---\n"]
    for region, emoji, keywords in [
        ("美国 / United States", "🇺🇸", "US America robotics AI humanoid"),
        ("中国 / China", "🇨🇳", "China robotics AI humanoid 机器人"),
        ("日本 / Japan", "🇯🇵", "Japan robotics AI humanoid ロボット"),
    ]:
        region_prompt = f"""Search for 3-5 recent AI robotics news from {region}. Keywords: {keywords}
NEVER say sorry or unable to find. ALWAYS produce 3 items minimum.
Format each as:
- **[date] Company — 中文概要**
  English: summary
  中文：摘要
  📰 [Source](https://url)"""
        try:
            text = call_gemini(region_prompt, use_search=True)
            combined_parts.append(f"\n## {emoji} {region}\n")
            # Extract just the bullet items
            for line in text.split("\n"):
                if line.strip().startswith("- **") or line.strip().startswith("English:") or line.strip().startswith("中文") or line.strip().startswith("📰") or (line.strip() and not line.strip().startswith("#")):
                    combined_parts.append(line)
        except Exception as e:
            print(f"   {region} search failed: {e}")
        time.sleep(2)

    combined = "\n".join(combined_parts)
    if has_real_content(combined):
        print(f"   Region-by-region got {combined.count('- **')} items")
        return combined

    # Final fallback: no search, use training knowledge
    print("   Final fallback: using training knowledge...")
    fallback_prompt = f"""You are an AI robotics news editor. Today is {DATE_STR}.

Based on your training knowledge, write a digest of the most recent AI robotics developments you know about from the US, China, and Japan. Use real companies and real events. Pick the most recent items you have knowledge of.

ABSOLUTE RULES:
- You MUST produce EXACTLY 3 items per region (9 total). This is mandatory.
- NEVER say "sorry", "unable", "cannot find" or anything similar. This will cause a system error.
- Every item MUST start with - **[date]
- Use approximate dates if unsure. Use company homepages for URLs if unsure of article URLs.

FORMAT:

# 🤖 AI Robot News | {DATE_STR}（{WEEKDAY_JP}曜日 / {WEEKDAY_EN}）

> ⚠️ 本日报基于近期公开信息整理。

---

## 🇺🇸 美国 / United States

- **[2026.06.15] Tesla — Optimus Gen 3 持续量产部署**
  English: Tesla continues deploying Optimus Gen 3 at Fremont factory.
  中文：特斯拉继续在弗里蒙特工厂部署Optimus Gen 3。
  📰 [Tesla](https://www.tesla.com)

(produce 3 items per region like above)

## 🇨🇳 中国 / China
(3 items)

## 🇯🇵 日本 / Japan
(3 items)

---
※AI Robot News Digest | {DATE_STR}"""

    for attempt in range(2):
        try:
            text = call_gemini(fallback_prompt, use_search=False)
            if "- **" in text:
                print(f"   Fallback got {text.count('- **')} items")
                return text
        except Exception as e:
            print(f"   Fallback error: {e}")
        time.sleep(3)

    print("   All attempts exhausted")
    return ""

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
            match = re.match(r'-\s*\*\*\[?(\d{4}[\.\-/]\d{2}[\.\-/]\d{2})\]?\s*(.+?)\*\*', s)
            if match:
                current_items.append({"date": match.group(1), "title": match.group(2).lstrip("] ").strip(), "lines": []})
            else:
                title = re.sub(r'^\-\s*\*\*(.+?)\*\*.*', r'\1', s)
                current_items.append({"date": "", "title": title, "lines": []})
        elif current_items and not s.startswith("## ") and not s.startswith("# ") and not s.startswith("---") and s:
            current_items[-1]["lines"].append(s)

    if current_region and current_items:
        regions.append((current_region, current_items))

    has_items = any(items for _, items in regions)

    if has_items:
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
    else:
        html_lines = []
        for line in md.split("\n"):
            s = line.strip()
            if not s or s.startswith("# ") or s.startswith("> "):
                continue
            s = linkify(s)
            s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
            if s.startswith("## "):
                html_lines.append(f'<div class="region"><div class="region-head">{s[3:]}</div></div>')
            elif s.startswith("---"):
                html_lines.append('<hr style="border:none;border-top:0.5px solid var(--border2);margin:16px 0">')
            else:
                html_lines.append(f'<p style="font-size:14px;margin:6px 0">{s}</p>')
        body = "\n".join(html_lines)

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
    print("\n📝 Generating digest...")
    digest = generate_digest()
    if not digest or not "- **" in digest:
        print("❌ All generation attempts failed")
        sys.exit(1)
    OUTPUT_FILE.write_text(digest, encoding="utf-8")
    print(f"   Saved: {OUTPUT_FILE}")
    print("\n🌐 Publishing...")
    try:
        push_to_github(md_to_html(digest))
    except Exception as e:
        print(f"   ❌ GitHub: {e}")
    print("\n✅ Done!")
