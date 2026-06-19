#!/usr/bin/env python3
import os, subprocess, re
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))
TODAY = datetime.now(JST)
DATE_STR = TODAY.strftime("%Y.%m.%d")
WEEKDAY_MAP = {0:"月",1:"火",2:"水",3:"木",4:"金",5:"土",6:"日"}
WEEKDAY_EN = TODAY.strftime("%A")
WEEKDAY_JP = WEEKDAY_MAP[TODAY.weekday()]

OUTPUT_DIR = Path.home() / "ai-robot-news"
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / f"AI_Robot_News_{TODAY.strftime('%Y%m%d')}.md"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GITHUB_USER = "roboticsdao"
GITHUB_REPO = "ai-robot-news"
PAGE_URL = f"https://{GITHUB_USER}.github.io/{GITHUB_REPO}/latest.html"

def generate_digest():
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"""你是一个AI机器人行业新闻编辑。今天是 {DATE_STR}（{WEEKDAY_JP}曜日 / {WEEKDAY_EN}）。
请搜索过去24小时内美国、中国和日本的AI机器人领域重大新闻，整理成日报。
格式要求：
- 标题：🤖 AI Robot News | {DATE_STR}（{WEEKDAY_JP}曜日 / {WEEKDAY_EN}）
- 开头加一句信息时效性注意事项
- 按国家分类：🇺🇸 美国 / 🇨🇳 中国 / 🇯🇵 日本
- 每条新闻用 bullet point，包含：公司名、事件概要、出典来源名、原文URL
- 每条新闻一行英文，一行中文
- 末尾标注：※AI Robot News Digest
- 每个国家只选3-5条重要新闻
- 输出纯 Markdown"""
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
    lines = md.split("\n")
    html_lines = []
    for line in lines:
        if line.startswith("# "):
            html_lines.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            html_lines.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("### "):
            html_lines.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("- **"):
            line = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
            html_lines.append(f"<li>{line[2:]}</li>")
        elif line.startswith("- "):
            html_lines.append(f"<li>{line[2:]}</li>")
        elif line.startswith("---"):
            html_lines.append("<hr>")
        elif line.startswith(">"):
            html_lines.append(f"<blockquote>{line[1:].strip()}</blockquote>")
        elif line.strip() == "":
            html_lines.append("<br>")
        else:
            line = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
            line = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\\2">\\1</a>', line)
            html_lines.append(f"<p>{line}</p>")
    body = "\n".join(html_lines)
    return f'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Robot News | {DATE_STR}</title>
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans",sans-serif;max-width:680px;margin:0 auto;padding:24px 16px;background:#fafafa;color:#1a1a1a;line-height:1.7}}
  h1{{font-size:22px;margin:16px 0 8px}}
  h2{{font-size:18px;margin:24px 0 12px;padding-top:16px;border-top:2px solid #e0e0e0}}
  li{{list-style:none;padding:12px 16px;margin:8px 0;background:#fff;border-radius:10px;border:1px solid #e8e8e8;font-size:14px}}
  li strong{{color:#0066cc}}
  p{{font-size:14px;margin:4px 0}}
  a{{color:#0066cc;text-decoration:none}}
  blockquote{{font-size:13px;color:#666;padding:8px 12px;border-left:3px solid #ddd;margin:8px 0}}
  hr{{border:none;border-top:1px solid #e0e0e0;margin:16px 0}}
  @media(prefers-color-scheme:dark){{body{{background:#1a1a1a;color:#e0e0e0}}li{{background:#2a2a2a;border-color:#3a3a3a}}li strong{{color:#4da6ff}}h2{{border-top-color:#3a3a3a}}blockquote{{color:#999;border-left-color:#444}}a{{color:#4da6ff}}}}
</style>
</head>
<body>{body}</body>
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
    print(f"✅ GitHub Pages: {PAGE_URL}")

def extract_headlines(md, max_items=3):
    headlines = []
    for line in md.split("\n"):
        if line.startswith("- **") and len(headlines) < max_items:
            match = re.search(r'\*\*(.+?)\*\*', line)
            if match:
                headlines.append("* " + match.group(1).split("—")[0].strip())
    return "\n".join(headlines) if headlines else "AI Robot News"

def add_to_calendar(md_content):
    title = "🤖 AI Robot News | " + DATE_STR
    headlines = extract_headlines(md_content)
    notes_ics = headlines.replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")
    event_date = TODAY.replace(hour=9, minute=0, second=0)
    end_date = TODAY.replace(hour=9, minute=15, second=0)
    start = event_date.strftime("%Y%m%dT%H%M%S")
    end = end_date.strftime("%Y%m%dT%H%M%S")
    ics = "BEGIN:VCALENDAR\n"
    ics += "VERSION:2.0\n"
    ics += "PRODID:-//AI Robot News//EN\n"
    ics += "BEGIN:VEVENT\n"
    ics += "DTSTART;TZID=Asia/Tokyo:" + start + "\n"
    ics += "DTEND;TZID=Asia/Tokyo:" + end + "\n"
    ics += "SUMMARY:" + title + "\n"
    ics += "DESCRIPTION:" + notes_ics + "\n"
    ics += "URL:" + PAGE_URL + "\n"
    ics += "BEGIN:VALARM\n"
    ics += "TRIGGER:-PT5M\n"
    ics += "ACTION:DISPLAY\n"
    ics += "DESCRIPTION:AI Robot News\n"
    ics += "END:VALARM\n"
    ics += "END:VEVENT\n"
    ics += "END:VCALENDAR\n"
    ics_file = OUTPUT_DIR / ("AI_Robot_News_" + TODAY.strftime("%Y%m%d") + ".ics")
    ics_file.write_text(ics, encoding="utf-8")
    subprocess.run(["open", str(ics_file)], check=True)
    print("✅ Calendar: event with URL -> " + PAGE_URL)

if __name__ == "__main__":
    print(f"🤖 AI Robot News Digest — {DATE_STR} ({WEEKDAY_JP})")
    print("=" * 50)
    print("\n📝 Step 1: Generating digest (Gemini + Google Search)...")
    digest = generate_digest()
    OUTPUT_FILE.write_text(digest, encoding="utf-8")
    print(f"   Saved: {OUTPUT_FILE}")
    print("\n🌐 Step 2: Publishing to GitHub Pages...")
    try:
        html_content = md_to_html(digest)
        push_to_github(html_content)
    except Exception as e:
        print(f"❌ GitHub: {e}")
    print("\n📅 Step 3: Adding to Calendar...")
    try:
        add_to_calendar(digest)
    except Exception as e:
        print(f"❌ Calendar: {e}")
    print("\n✅ Done!")
