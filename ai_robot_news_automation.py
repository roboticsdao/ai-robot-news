#!/usr/bin/env python3
import html
import os, subprocess, re, sys, time, json, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

LOCAL_TZ = timezone(timedelta(hours=9))
TODAY = datetime.now(LOCAL_TZ)
DATE_STR = TODAY.strftime("%Y.%m.%d")
TIME_STR = TODAY.strftime("%H:%M")
CUTOFF_DATE = (TODAY - timedelta(days=3)).date()
WEEKDAY_MAP = {0:"月",1:"火",2:"水",3:"木",4:"金",5:"土",6:"日"}
WEEKDAY_EN = TODAY.strftime("%A")
WEEKDAY_JP = WEEKDAY_MAP[TODAY.weekday()]
IS_CI = os.environ.get("CI","") == "true"
OUTPUT_DIR = Path.cwd() if IS_CI else (Path.home() / "ai-robot-news")
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / f"AI_Robot_News_{TODAY.strftime('%Y%m%d')}.md"
HISTORY_FILE = OUTPUT_DIR / "history.json"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY","")
PAGE_URL = "https://roboticsdao.github.io/ai-robot-news/latest.html"

REGIONS = [
    {
        "emoji": "🇺🇸",
        "label": "美国 / United States",
        "query": '("AI robotics" OR "humanoid robot" OR "robotics startup") (US OR America OR Tesla OR Figure OR Boston Dynamics)',
        "hl": "en-US",
        "gl": "US",
        "ceid": "US:en",
    },
    {
        "emoji": "🇨🇳",
        "label": "中国 / China",
        "query": '("AI robotics" OR "humanoid robot" OR 机器人 OR 具身智能) (China OR 中国 OR Unitree OR 宇树 OR UBTech OR 优必选)',
        "hl": "zh-CN",
        "gl": "CN",
        "ceid": "CN:zh-Hans",
    },
    {
        "emoji": "🇯🇵",
        "label": "日本 / Japan",
        "query": "日本 ロボット AI",
        "queries": [
            "日本 ロボット AI",
            "国内 ロボット AI",
            "日本 ヒューマノイド ロボット",
            "日本 フィジカルAI ロボット",
            "ソニー アイボ ロボット",
            "AGRIST 収穫ロボット AI",
            "ファナック ロボット AI",
            "安川電機 ロボット AI",
        ],
        "hl": "ja",
        "gl": "JP",
        "ceid": "JP:ja",
        "exclude_terms": ["中国", "China", "中国製", "中国経済", "人民網", "Unitree", "ユニツリー", "宇樹", "宇树", "매일경제", "디지털투데이"],
    },
]

PROMPT = f"""You are an AI robotics industry news editor. Today is {DATE_STR} ({WEEKDAY_EN}).

Search for the latest AI robotics news. Find 3-5 items for EACH of these 3 regions: United States, China, Japan. Total 9-15 items.

RULES:
1. Prioritize last 24 hours. Expand only to the past 3 days if needed. NEVER use older items.
2. NEVER say sorry, unable to find, or anything similar. FORBIDDEN.
3. Each item must have: date, company name, English summary, Chinese summary, source publication name.
4. Japan section must cover Japan's domestic AI/robotics industry only. Exclude China/Unitree stories merely reported in Japanese.
5. Do NOT include any URLs in your response. I will add them separately.

FORMAT (pure Markdown, no code fences):

# 🤖 AI Robot News | {DATE_STR}（{WEEKDAY_JP}曜日 / {WEEKDAY_EN}）

> ⚠️ 本日报优先收录24小时内新闻，不足部分仅回溯至近3天。

---

## 🇺🇸 美国 / United States

- **[{DATE_STR}] Company Name — 中文事件概要**
  English: One-line English summary.
  中文：一行中文摘要。
  📰 Source Publication Name

(3-5 items per region, same format for all 3 regions)

## 🇨🇳 中国 / China

## 🇯🇵 日本 / Japan

---
※AI Robot News Digest | {DATE_STR}"""

CSS = """:root{--bg:#fff;--fg:#1a1a1a;--fg2:#6b6b6f;--fg3:#9a9a9e;--border:#d4d4d4;--border2:#e8e8e8;--serif:Georgia,"Times New Roman",serif;--sans:-apple-system,BlinkMacSystemFont,"Helvetica Neue",sans-serif;--link:#1a6ed8;--hover:#f5f5f5;--menu-bg:#fff;--menu-shadow:rgba(0,0,0,0.12)}
@media(prefers-color-scheme:dark){:root{--bg:#1a1a1a;--fg:#e2e2e2;--fg2:#a0a0a0;--fg3:#707070;--border:#444;--border2:#333;--link:#6db3f8;--hover:#2a2a2a;--menu-bg:#252525;--menu-shadow:rgba(0,0,0,0.4)}}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:var(--sans);margin:0 auto;padding:28px 24px;background:var(--bg);color:var(--fg);line-height:1.75;font-size:15px;-webkit-font-smoothing:antialiased;max-width:780px}
@media(max-width:600px){body{padding:20px 16px}}
.top-bar{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}
.history-wrap{position:relative}
.history-btn{background:var(--menu-bg);border:1px solid var(--border);border-radius:8px;padding:6px 12px;font-size:12px;color:var(--fg2);cursor:pointer;display:flex;align-items:center;gap:4px;font-family:var(--sans)}
.history-btn:hover{background:var(--hover)}
.history-btn svg{width:14px;height:14px;fill:var(--fg3)}
.history-panel{display:none;position:absolute;top:36px;left:0;background:var(--menu-bg);border:1px solid var(--border);border-radius:10px;box-shadow:0 8px 24px var(--menu-shadow);min-width:280px;max-height:400px;overflow-y:auto;z-index:100}
.history-panel.open{display:block}
.history-panel h3{font-size:12px;color:var(--fg3);padding:10px 14px 6px;font-weight:600;position:sticky;top:0;background:var(--menu-bg)}
.history-item{display:flex;justify-content:space-between;align-items:center;padding:8px 14px;border-bottom:0.5px solid var(--border2);font-size:13px;cursor:pointer;transition:background .1s}
.history-item:hover{background:var(--hover)}
.history-item:last-child{border-bottom:none}
.history-item .date{color:var(--fg);font-weight:500}
.history-item .time{color:var(--fg3);font-size:11px;margin-left:8px}
.history-item .del-btn{color:var(--fg3);font-size:11px;padding:2px 6px;border:1px solid var(--border2);border-radius:4px;background:transparent;cursor:pointer;opacity:0;transition:opacity .15s}
.history-item:hover .del-btn{opacity:1}
.history-item .del-btn:hover{color:#e55;border-color:#e55}
.history-current{background:var(--hover)}
.history-empty{padding:20px 14px;text-align:center;color:var(--fg3);font-size:12px}
.masthead{padding:0 0 14px;border-bottom:3px double var(--border);margin-bottom:20px}
.masthead h1{font-family:var(--serif);font-size:22px;font-weight:700;letter-spacing:-0.5px}
.masthead .date{font-size:12px;color:var(--fg3);margin-top:3px}
.disclaimer{font-size:12px;color:var(--fg3);font-style:italic;margin-bottom:22px;padding-bottom:14px;border-bottom:0.5px solid var(--border2)}
.region{margin-bottom:12px;padding-bottom:20px;border-bottom:2.5px solid var(--border)}
.region:last-child{border-bottom:none}
.region-head{font-family:var(--serif);font-size:17px;font-weight:700;padding:12px 0 8px;border-bottom:1.5px solid var(--border);margin-bottom:12px}
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

HISTORY_JS = '<script>(function(){var B=window.location.href.replace(/\\/[^/]*$/,""),btn=document.getElementById("historyBtn"),panel=document.getElementById("historyPanel"),list=document.getElementById("historyList"),H=[],hid=JSON.parse(localStorage.getItem("hidden_dates")||"[]");btn.onclick=function(e){e.stopPropagation();panel.classList.toggle("open");if(panel.classList.contains("open"))load()};document.onclick=function(){panel.classList.remove("open")};panel.onclick=function(e){e.stopPropagation()};function load(){fetch(B+"/history.json?"+Date.now()).then(function(r){return r.json()}).then(function(d){H=d.filter(function(x){return hid.indexOf(x.id)===-1});render()}).catch(function(){list.innerHTML=\'<div class="history-empty">暂无历史记录</div>\'})}function render(){if(!H.length){list.innerHTML=\'<div class="history-empty">暂无历史记录</div>\';return}var c=window.location.pathname.split("/").pop();list.innerHTML=H.map(function(h){var ic=(c===h.file||(c==="latest.html"&&h===H[0]));return\'<div class="history-item \'+(ic?"history-current":"")+\'" data-file="\'+h.file+\'"><div><span class="date">\'+h.date+\'</span><span class="time">\'+h.time+\'</span></div><div style="display:flex;align-items:center;gap:6px"><span class="items">\'+h.count+\' items</span><button class="del-btn" data-id="\'+h.id+\'">✕</button></div></div>\'}).join("");list.querySelectorAll(".history-item").forEach(function(el){el.onclick=function(){window.location.href=B+"/"+this.dataset.file}});list.querySelectorAll(".del-btn").forEach(function(el){el.onclick=function(e){e.stopPropagation();var id=this.dataset.id;hid.push(id);localStorage.setItem("hidden_dates",JSON.stringify(hid));H=H.filter(function(h){return h.id!==id});render()}})}})();</script>'

def generate_digest():
    if not GEMINI_API_KEY:
        print("   GEMINI_API_KEY is missing; using Google News RSS fallback")
        return generate_digest_from_rss()

    from google import genai
    from google.genai import types
    client = genai.Client(api_key=GEMINI_API_KEY)
    for attempt in range(3):
        try:
            print(f"   Attempt {attempt+1}/3...")
            resp = client.models.generate_content(
                model="gemini-2.0-flash-lite",
                contents=PROMPT,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    temperature=0.3,
                ),
            )
            text = resp.text or ""
            if has_recent_content(text) and text.count("- **") >= 6:
                print(f"   Got {text.count('- **')} items")
                return text
            if has_recent_content(text) and text.count("- **") >= 3:
                print(f"   Got {text.count('- **')} items (partial)")
                return text
            print(f"   Only {text.count('- **')} items, retrying...")
        except Exception as e:
            err = str(e)
            if "429" in err:
                wait = 65
                m = re.search(r'retry in (\d+)', err.lower())
                if m:
                    wait = int(m.group(1)) + 5
                print(f"   Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            print(f"   Error: {err[:100]}")
        time.sleep(5)
    print("   Gemini did not return enough grounded items; using Google News RSS fallback")
    return generate_digest_from_rss()

def strip_html(value):
    value = re.sub(r"<[^>]+>", " ", value or "")
    return html.unescape(re.sub(r"\s+", " ", value)).strip()

def parse_google_news_title(title):
    title = strip_html(title)
    if " - " in title:
        headline, source = title.rsplit(" - ", 1)
        return headline.strip(), source.strip()
    return title, "Google News"

def parse_item_date(value):
    for fmt in ("%Y.%m.%d", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None

def has_recent_content(text):
    dates = re.findall(r'-\s*\*\*\[(\d{4}[\.\-/]\d{2}[\.\-/]\d{2})\]', text or "")
    if not dates:
        return False
    return all((parse_item_date(d) or TODAY.date()) >= CUTOFF_DATE for d in dates)

def fetch_rss_items(region, limit=5):
    items = []
    seen = set()
    exclude_terms = region.get("exclude_terms", [])
    queries = region.get("queries") or [region["query"]]
    for query in queries:
        params = {
            "q": f"{query} when:3d -中国 -China -Unitree -ユニツリー",
            "hl": region["hl"],
            "gl": region["gl"],
            "ceid": region["ceid"],
        }
        url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as response:
            xml = response.read()

        root = ET.fromstring(xml)
        for node in root.findall("./channel/item"):
            raw_title = node.findtext("title", "")
            link = node.findtext("link", "")
            published = node.findtext("pubDate", "")
            headline, source = parse_google_news_title(raw_title)
            if not headline or headline.lower() in seen:
                continue
            combined = f"{headline} {source}"
            if any(term.lower() in combined.lower() for term in exclude_terms):
                continue
            seen.add(headline.lower())
            try:
                dt = datetime.strptime(published, "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=timezone.utc).astimezone(LOCAL_TZ)
                date = dt.strftime("%Y.%m.%d")
            except Exception:
                date = DATE_STR
            if parse_item_date(date) < CUTOFF_DATE:
                continue
            items.append({"date": date, "headline": headline, "source": source, "link": link})
            if len(items) >= limit:
                return items
    return items

def generate_digest_from_rss():
    parts = [
        f"# 🤖 AI Robot News | {DATE_STR}（{WEEKDAY_JP}曜日 / {WEEKDAY_EN}）",
        "",
        "> ⚠️ 本日报使用 Google News RSS 自动收录近3天 AI 机器人相关新闻；Gemini API 不可用或额度耗尽时会启用此兜底。",
        "",
        "---",
    ]

    total = 0
    for region in REGIONS:
        print(f"   RSS fallback: {region['emoji']} {region['label']}")
        try:
            items = fetch_rss_items(region)
        except Exception as e:
            print(f"   RSS error for {region['label']}: {e}")
            items = []

        parts.append(f"\n## {region['emoji']} {region['label']}\n")
        if not items:
            parts.append(f"- **[{DATE_STR}] No RSS result — 暂无可验证 RSS 新闻**\n  English: Google News RSS returned no recent result for this region.\n  中文：本地区暂未抓取到可验证的 Google News RSS 结果。\n  📰 Google News")
            continue

        for item in items:
            total += 1
            parts.append(
                f"- **[{item['date']}] {item['source']} — {item['headline']}**\n"
                f"  English: {item['headline']}\n"
                f"  中文：新闻标题：{item['headline']}\n"
                f"  📰 [{item['source']}]({item['link']})"
            )

    parts.append(f"\n---\n※AI Robot News Digest | {DATE_STR} | RSS fallback items: {total}")
    return "\n\n".join(parts)

def make_search_link(title):
    clean = re.sub(r'\[\d{4}[\.\-/]\d{2}[\.\-/]\d{2}\]\s*', '', title)
    clean = re.sub(r'[—\-]\s*', ' ', clean).strip()[:80]
    if not clean:
        return ""
    return "https://news.google.com/search?q=" + urllib.parse.quote(clean)

DATE_RE = re.compile(r'-\s*\*\*\[(\d{4}[\.\-/]\d{2}[\.\-/]\d{2})\]\s*(.+?)\*\*')

def md_to_html(md):
    regions, cur, items, discl = [], None, [], ""
    for line in md.split("\n"):
        s = line.strip()
        if s.startswith("> "):
            discl = s[2:].strip()
        elif s.startswith("## "):
            if cur and items:
                regions.append((cur, items))
            h = s[3:].strip()
            f = ""
            for e in ["🇺🇸","🇨🇳","🇯🇵"]:
                if e in h:
                    f = e
                    break
            cur = (f, h.replace(f,"").strip())
            items = []
        elif s.startswith("- **"):
            m = DATE_RE.match(s)
            if m:
                items.append({"date": m.group(1), "title": m.group(2).strip(), "lines": []})
            else:
                t = re.sub(r'^\-\s*\*\*(.+?)\*\*.*', r'\1', s)
                items.append({"date": "", "title": t, "lines": []})
        elif items and not s.startswith("## ") and not s.startswith("# ") and not s.startswith("---") and s:
            items[-1]["lines"].append(s)
    if cur and items:
        regions.append((cur, items))

    parts = []
    for (flag, label), itms in regions:
        parts.append(f'<div class="region"><div class="region-head">{flag} {label}</div>')
        for it in itms:
            en = zh = src_name = src_url = ""
            for ln in it["lines"]:
                if ln.startswith("📰"):
                    src_name = ln.replace("📰","").strip()
                    m = re.search(r'\[([^\]]+)\]\((https?://[^\)]+)\)', src_name)
                    if m:
                        src_name = m.group(1).strip()
                        src_url = m.group(2).strip()
                    else:
                        url_m = re.search(r'(https?://\S+)', src_name)
                        if url_m:
                            src_url = url_m.group(1).strip()
                        src_name = re.sub(r'\[([^\]]+)\].*', r'\1', src_name)
                        src_name = re.sub(r'https?://\S+', '', src_name).strip().rstrip("|").strip()
                elif ln.lower().startswith("english:") or ln.lower().startswith("en:"):
                    en = ln.split(":", 1)[1].strip()
                elif "中文" in ln[:4]:
                    zh = re.split(r'[：:]', ln, maxsplit=1)[-1].strip()
                elif not en and not any('\u4e00' <= c <= '\u9fff' for c in ln[:10]):
                    en = ln
                elif not zh:
                    zh = ln
            search_url = src_url or make_search_link(it["title"])
            if not src_name:
                src_name = "Google News"
            src_html = f'<div class="item-src">📰 <a href="{search_url}" target="_blank">{src_name} ↗</a></div>' if search_url else f'<div class="item-src">📰 {src_name}</div>'
            parts.append(
                f'<div class="item">'
                f'<div class="item-date">{it["date"]}</div>'
                f'<div class="item-title">{it["title"]}</div>'
                f'{"<p class=item-en>" + en + "</p>" if en else ""}'
                f'{"<p class=item-zh>" + zh + "</p>" if zh else ""}'
                f'{src_html}</div>'
            )
        parts.append('</div>')
    body = "\n".join(parts)
    if not discl:
        discl = "⚠ 本日报优先收录24小时内新闻，不足部分回溯至近两周。"

    return f'''<!DOCTYPE html>
<html lang="zh"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>AI Robot News | {DATE_STR}</title><style>{CSS}</style></head><body>
<div class="top-bar"><div class="history-wrap"><button class="history-btn" id="historyBtn"><svg viewBox="0 0 16 16"><path d="M8 1a7 7 0 1 0 0 14A7 7 0 0 0 8 1zm0 12.5A5.5 5.5 0 1 1 8 2.5a5.5 5.5 0 0 1 0 11zM8.5 4h-1v4.5l3.5 2 .5-.87-3-1.75V4z"/></svg>历史记录</button><div class="history-panel" id="historyPanel"><h3>📅 刷新记录</h3><div id="historyList"></div></div></div><div style="font-size:11px;color:var(--fg3)">更新于 {TIME_STR} JST</div></div>
<div class="masthead"><h1>AI Robot News</h1><div class="date">{DATE_STR} — {WEEKDAY_EN} / {WEEKDAY_JP}曜日</div></div>
<div class="disclaimer">{discl}</div>
{body}
<div class="footer">※ AI Robot News Digest · roboticsdao.github.io</div>
{HISTORY_JS}</body></html>'''

def update_history(n):
    h = []
    if HISTORY_FILE.exists():
        try: h = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except: pass
    e = {"id": TODAY.strftime("%Y%m%d_%H%M"), "date": DATE_STR, "time": TIME_STR + " JST",
         "file": f"AI_Robot_News_{TODAY.strftime('%Y%m%d')}.html", "count": n}
    h = [x for x in h if x["date"] != DATE_STR]
    h.insert(0, e)
    h = h[:90]
    HISTORY_FILE.write_text(json.dumps(h, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    print(f"🤖 AI Robot News — {DATE_STR} ({WEEKDAY_JP})")
    print("=" * 50)
    print("\n📝 Generating digest...")
    digest = generate_digest()
    n = digest.count("- **") if digest else 0
    if n < 3:
        print(f"❌ Only {n} items")
        sys.exit(1)
    OUTPUT_FILE.write_text(digest, encoding="utf-8")
    html = md_to_html(digest)
    (OUTPUT_DIR / "latest.html").write_text(html, encoding="utf-8")
    dated = OUTPUT_DIR / f"AI_Robot_News_{TODAY.strftime('%Y%m%d')}.html"
    dated.write_text(html, encoding="utf-8")
    update_history(n)
    print(f"   Total: {n} items")
    print(f"   Saved: {OUTPUT_FILE}")
    if not IS_CI:
        os.chdir(str(OUTPUT_DIR))
        subprocess.run(["git","add","latest.html",dated.name,OUTPUT_FILE.name,"history.json"], check=True)
        r = subprocess.run(["git","diff","--cached","--quiet"])
        if r.returncode != 0:
            subprocess.run(["git","commit","-m",f"update {DATE_STR}"], check=True)
            subprocess.run(["git","push"], check=True)
            print(f"   ✅ {PAGE_URL}")
    print("\n✅ Done!")
