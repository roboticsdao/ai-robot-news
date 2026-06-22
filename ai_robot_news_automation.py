#!/usr/bin/env python3
import os, subprocess, re, sys, time, json
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))
TODAY = datetime.now(JST)
DATE_STR = TODAY.strftime("%Y.%m.%d")
TIME_STR = TODAY.strftime("%H:%M")
WEEKDAY_MAP = {0:"月",1:"火",2:"水",3:"木",4:"金",5:"土",6:"日"}
WEEKDAY_EN = TODAY.strftime("%A")
WEEKDAY_JP = WEEKDAY_MAP[TODAY.weekday()]

IS_CI = os.environ.get("CI", "") == "true"
OUTPUT_DIR = Path.cwd() if IS_CI else (Path.home() / "ai-robot-news")
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / f"AI_Robot_News_{TODAY.strftime('%Y%m%d')}.md"
HISTORY_FILE = OUTPUT_DIR / "history.json"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
PAGE_URL = "https://roboticsdao.github.io/ai-robot-news/latest.html"

REGIONS = [
    ("🇺🇸", "美国 / United States", "US AI robotics humanoid robot Tesla Optimus Figure Boston Dynamics"),
    ("🇨🇳", "中国 / China", "China AI robotics humanoid robot 中国 机器人 Unitree 宇树 小鹏 优必选"),
    ("🇯🇵", "日本 / Japan", "Japan AI robotics humanoid robot 日本 ロボット Honda Fanuc Telexistence Toyota"),
]

CSS = """
:root{--bg:#fff;--fg:#1a1a1a;--fg2:#6b6b6f;--fg3:#9a9a9e;--border:#d4d4d4;--border2:#e8e8e8;--serif:Georgia,"Times New Roman",serif;--sans:-apple-system,BlinkMacSystemFont,"Helvetica Neue",sans-serif;--link:#1a6ed8;--hover:#f5f5f5;--menu-bg:#fff;--menu-shadow:rgba(0,0,0,0.12)}
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
.history-panel h3{font-size:12px;color:var(--fg3);padding:10px 14px 6px;font-weight:600;letter-spacing:0.3px;position:sticky;top:0;background:var(--menu-bg)}
.history-item{display:flex;justify-content:space-between;align-items:center;padding:8px 14px;border-bottom:0.5px solid var(--border2);font-size:13px;cursor:pointer;transition:background .1s}
.history-item:hover{background:var(--hover)}
.history-item:last-child{border-bottom:none}
.history-item .date{color:var(--fg);font-weight:500}
.history-item .time{color:var(--fg3);font-size:11px;margin-left:8px}
.history-item .items{color:var(--fg3);font-size:11px}
.history-item .del-btn{color:var(--fg3);font-size:11px;padding:2px 6px;border:1px solid var(--border2);border-radius:4px;background:transparent;cursor:pointer;opacity:0;transition:opacity .15s}
.history-item:hover .del-btn{opacity:1}
.history-item .del-btn:hover{color:#e55;border-color:#e55}
.history-current{background:var(--hover);font-weight:600}
.history-empty{padding:20px 14px;text-align:center;color:var(--fg3);font-size:12px}
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

HISTORY_JS = """
<script>
(function(){
  const BASE = window.location.href.replace(/\\/[^/]*$/, '');
  const btn = document.getElementById('historyBtn');
  const panel = document.getElementById('historyPanel');
  const list = document.getElementById('historyList');
  let history = [];
  let hidden = JSON.parse(localStorage.getItem('hidden_dates') || '[]');

  btn.addEventListener('click', function(e){
    e.stopPropagation();
    panel.classList.toggle('open');
    if(panel.classList.contains('open')) loadHistory();
  });
  document.addEventListener('click', function(){ panel.classList.remove('open'); });
  panel.addEventListener('click', function(e){ e.stopPropagation(); });

  function loadHistory(){
    fetch(BASE + '/history.json?' + Date.now())
      .then(r => r.json())
      .then(data => {
        history = data.filter(d => !hidden.includes(d.id));
        render();
      })
      .catch(() => {
        list.innerHTML = '<div class="history-empty">暂无历史记录</div>';
      });
  }

  function render(){
    if(!history.length){
      list.innerHTML = '<div class="history-empty">暂无历史记录</div>';
      return;
    }
    let currentFile = window.location.pathname.split('/').pop();
    list.innerHTML = history.map(h => {
      let isCurrent = (currentFile === h.file || currentFile === 'latest.html' && h === history[0]);
      return `<div class="history-item ${isCurrent ? 'history-current' : ''}" data-file="${h.file}">
        <div><span class="date">${h.date}</span><span class="time">${h.time}</span></div>
        <div style="display:flex;align-items:center;gap:6px">
          <span class="items">${h.count} items</span>
          <button class="del-btn" data-id="${h.id}" onclick="event.stopPropagation()">✕</button>
        </div>
      </div>`;
    }).join('');

    list.querySelectorAll('.history-item').forEach(el => {
      el.addEventListener('click', function(){
        window.location.href = BASE + '/' + this.dataset.file;
      });
    });

    list.querySelectorAll('.del-btn').forEach(el => {
      el.addEventListener('click', function(){
        let id = this.dataset.id;
        hidden.push(id);
        localStorage.setItem('hidden_dates', JSON.stringify(hidden));
        history = history.filter(h => h.id !== id);
        render();
      });
    });
  }
})();
</script>
"""

def call_gemini(prompt, use_search=True):
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=GEMINI_API_KEY)
    config_args = {"temperature": 0.3}
    if use_search:
        config_args["tools"] = [types.Tool(google_search=types.GoogleSearch())]
    response = client.models.generate_content(
        model="gemini-2.5-flash", contents=prompt,
        config=types.GenerateContentConfig(**config_args))
    return response.text or ""

def fetch_section(emoji, label, keywords):
    prompt = f"""Search for 3 to 5 recent AI robotics news specifically from {label}.
Search keywords: {keywords}. Today is {DATE_STR}.
CRITICAL RULES:
- You MUST return 3-5 news items. NEVER return zero.
- Prioritize last 24 hours, then expand to 2 weeks if needed.
- NEVER say "sorry", "unable to find", "无法获取". This is FORBIDDEN.
- Each item MUST start with: - **[date] Company — Chinese summary**
- Source URL: use direct article URLs. NEVER use vertexaisearch.cloud.google.com URLs.
FORMAT:
- **[2026.06.19] Company — 中文事件概要**
  English: One-line English summary.
  中文：一行中文摘要。
  📰 [Source Name](https://direct-url)
(produce 3-5 items)"""
    for attempt in range(3):
        try:
            text = call_gemini(prompt, use_search=True)
            text = re.sub(r'https://vertexaisearch\.cloud\.google\.com/[^\s\)]+',
                          'https://www.google.com/search?q='+keywords.split()[0], text)
            if "- **" in text and "很抱歉" not in text and "无法获取" not in text:
                print(f"   {emoji} Got {text.count('- **')} items (attempt {attempt+1})")
                return text
        except Exception as e:
            print(f"   {emoji} Attempt {attempt+1} error: {e}")
        time.sleep(5)
    print(f"   {emoji} Fallback...")
    try:
        fb = f"Based on your knowledge, list 3 recent AI robotics news from {label}. Use real events. NEVER say sorry. Format: - **[date] Company — 中文概要**\n  English: summary\n  中文：摘要\n  📰 [Source](https://url)"
        text = call_gemini(fb, use_search=False)
        if "- **" in text: return text
    except: pass
    return ""

def generate_digest():
    header = f"# 🤖 AI Robot News | {DATE_STR}（{WEEKDAY_JP}曜日 / {WEEKDAY_EN}）\n\n> ⚠️ 本日报优先收录24小时内新闻，不足部分回溯至近两周。\n\n---\n"
    parts = [header]
    for emoji, label, kw in REGIONS:
        print(f"\n   Fetching {emoji} {label}...")
        content = fetch_section(emoji, label, kw)
        parts.append(f"\n## {emoji} {label}\n")
        parts.append(content if content else f"- **[{DATE_STR}] 暂无更新 — No updates**\n  English: No recent news.\n  中文：暂无新闻。")
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

def md_to_html(md, item_count=0):
    regions, current_region, current_items, disclaimer = [], None, [], ""
    for line in md.split("\n"):
        s = line.strip()
        if s.startswith("> "): disclaimer = s[2:].strip()
        elif s.startswith("## "):
            if current_region and current_items: regions.append((current_region, current_items))
            heading = s[3:].strip()
            flag = ""
            if "🇺🇸" in heading: flag = "🇺🇸"
            elif "🇨🇳" in heading: flag = "🇨🇳"
            elif "🇯🇵" in heading: flag = "🇯🇵"
            label = re.sub(r'[🇺🇸🇨🇳🇯🇵]\s*', '', heading).strip()
            current_region, current_items = (flag, label), []
        elif s.startswith("- **"):
            match = re.match(r'-\s*\*\*\[(\d{4}[\.\-/]\d{2}[\.\-/]\d{2})\]\s*(.+?)\*\*', s)
            if match: current_items.append({"date":match.group(1).strip(),"title":match.group(2).lstrip("] ").strip(),"lines":[]})
            else: current_items.append({"date":"","title":re.sub(r'^\-\s*\*\*(.+?)\*\*.*',r'\1',s),"lines":[]})
        elif current_items and not s.startswith("## ") and not s.startswith("# ") and not s.startswith("---") and s:
            current_items[-1]["lines"].append(s)
    if current_region and current_items: regions.append((current_region, current_items))

    parts = []
    for (flag, label), items in regions:
        parts.append(f'<div class="region"><div class="region-head">{flag} {label}</div>')
        for it in items:
            en_line = zh_line = src_html = ""
            for ln in it["lines"]:
                if ln.startswith("📰"):
                    src_html = f'<div class="item-src">📰 {linkify(ln.replace("📰","").strip())}</div>'
                elif ln.lower().startswith("english:") or ln.lower().startswith("en:"):
                    en_line = ln.split(":",1)[1].strip()
                elif "中文" in ln[:4]: zh_line = re.split(r'[：:]',ln,1)[-1].strip()
                elif not en_line and not any('\u4e00'<=c<='\u9fff' for c in ln[:10]): en_line = ln
                elif not zh_line: zh_line = ln
            parts.append(f'<div class="item"><div class="item-date">{it["date"]}</div><div class="item-title">{it["title"]}</div>{"<p class=item-en>"+en_line+"</p>" if en_line else ""}{"<p class=item-zh>"+zh_line+"</p>" if zh_line else ""}{src_html}</div>')
        parts.append('</div>')
    body = "\n".join(parts)
    if not disclaimer: disclaimer = "⚠ 本日报优先收录24小时内新闻，不足部分回溯至近两周。"

    return f'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Robot News | {DATE_STR}</title>
<style>{CSS}</style>
</head>
<body>
<div class="top-bar">
  <div class="history-wrap">
    <button class="history-btn" id="historyBtn">
      <svg viewBox="0 0 16 16"><path d="M8 1a7 7 0 1 0 0 14A7 7 0 0 0 8 1zm0 12.5A5.5 5.5 0 1 1 8 2.5a5.5 5.5 0 0 1 0 11zM8.5 4h-1v4.5l3.5 2 .5-.87-3-1.75V4z"/></svg>
      历史记录
    </button>
    <div class="history-panel" id="historyPanel">
      <h3>📅 刷新记录</h3>
      <div id="historyList"></div>
    </div>
  </div>
  <div style="font-size:11px;color:var(--fg3)">更新于 {TIME_STR} JST</div>
</div>
<div class="masthead"><h1>AI Robot News</h1><div class="date">{DATE_STR} — {WEEKDAY_EN} / {WEEKDAY_JP}曜日</div></div>
<div class="disclaimer">{disclaimer}</div>
{body}
<div class="footer">※ AI Robot News Digest · roboticsdao.github.io</div>
{HISTORY_JS}
</body>
</html>'''

def update_history(item_count):
    history = []
    if HISTORY_FILE.exists():
        try: history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except: history = []
    entry = {
        "id": TODAY.strftime("%Y%m%d_%H%M"),
        "date": DATE_STR,
        "time": TIME_STR + " JST",
        "weekday": f"{WEEKDAY_JP}曜日 / {WEEKDAY_EN}",
        "file": f"AI_Robot_News_{TODAY.strftime('%Y%m%d')}.html",
        "count": item_count,
    }
    # Replace same-day entry or prepend
    history = [h for h in history if h["date"] != DATE_STR] 
    history.insert(0, entry)
    # Keep last 90 days
    history = history[:90]
    HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    return history

def push_to_github(html_content, item_count):
    (OUTPUT_DIR / "latest.html").write_text(html_content, encoding="utf-8")
    dated = OUTPUT_DIR / f"AI_Robot_News_{TODAY.strftime('%Y%m%d')}.html"
    dated.write_text(html_content, encoding="utf-8")
    update_history(item_count)
    os.chdir(str(OUTPUT_DIR))
    subprocess.run(["git","add","latest.html",dated.name,"history.json"], check=True)
    result = subprocess.run(["git","diff","--cached","--quiet"])
    if result.returncode != 0:
        subprocess.run(["git","commit","-m",f"update {DATE_STR}"], check=True)
        subprocess.run(["git","push"], check=True)
        print(f"   ✅ Published: {PAGE_URL}")
    else:
        print("   No changes")

if __name__ == "__main__":
    print(f"🤖 AI Robot News — {DATE_STR} ({WEEKDAY_JP})")
    print("=" * 50)
    print("\n📝 Generating digest...")
    digest = generate_digest()
    if not digest or digest.count("- **") < 3:
        print("❌ Failed"); sys.exit(1)
    item_count = digest.count("- **")
    OUTPUT_FILE.write_text(digest, encoding="utf-8")
    print(f"\n   Total: {item_count} items")
    print("\n🌐 Publishing...")
    try: push_to_github(md_to_html(digest, item_count), item_count)
    except Exception as e: print(f"   ❌ {e}")
    print("\n✅ Done!")
