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
3. Each item must have: date, company name, a substantial summary, and source publication name.
4. Japan section must cover Japan's domestic AI/robotics industry only. Exclude China/Unitree stories merely reported in Japanese.
5. Do NOT include any URLs in your response. I will add them separately.

FORMAT (pure Markdown, no code fences):

# 🤖 AI Robot News | {DATE_STR}（{WEEKDAY_JP}曜日 / {WEEKDAY_EN}）

> ⚠️ 本日报优先收录24小时内新闻，不足部分仅回溯至近3天。

---

## 🇺🇸 美国 / United States

- **[{DATE_STR}] Company Name — 中文事件概要**
  English: Summary in about 400 characters, covering what happened, why it matters, and what to watch next.
  中文：约300字中文总结，说明事件、产业意义和后续观察点。
  📰 Source Publication Name

(3-5 items per region, same format for all 3 regions)

## 🇨🇳 中国 / China

## 🇯🇵 日本 / Japan

---
※AI Robot News Digest | {DATE_STR}"""

CSS = """:root{--bg:#fff;--fg:#1a1a1a;--fg2:#6b6b6f;--fg3:#9a9a9e;--border:#d4d4d4;--border2:#e8e8e8;--serif:Georgia,"Times New Roman",serif;--sans:-apple-system,BlinkMacSystemFont,"Helvetica Neue",sans-serif;--link:#1a6ed8;--hover:#f5f5f5;--menu-bg:#fff;--menu-shadow:rgba(0,0,0,0.12)}
@media(prefers-color-scheme:dark){:root{--bg:#1a1a1a;--fg:#e2e2e2;--fg2:#a0a0a0;--fg3:#707070;--border:#444;--border2:#333;--link:#6db3f8;--hover:#2a2a2a;--menu-bg:#252525;--menu-shadow:rgba(0,0,0,0.4)}}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:var(--sans);margin:0 auto;padding:28px 0;background:var(--bg);color:var(--fg);line-height:1.75;font-size:15px;-webkit-font-smoothing:antialiased;width:calc(100vw - 48px)}
@media(max-width:760px){body{width:calc(100vw - 32px);padding:20px 0}}
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
.item-jp{font-size:13px;color:var(--fg);line-height:1.7;margin:0 0 4px}
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

def extract_entities(headline):
    names = [
        "Boston Dynamics", "Hyundai", "Tesla", "Figure", "NVIDIA", "Amazon", "Microsoft", "Google",
        "Unitree", "宇树", "优必选", "UBTech", "小鹏", "华为", "阿里巴巴", "腾讯", "百度",
        "AGRIST", "Sony", "ソニー", "aibo", "ファナック", "安川電機", "Telexistence", "SoftBank", "GMO", "Toyota", "Honda",
    ]
    found = [name for name in names if name.lower() in headline.lower()]
    return found[:4] or ["the companies and institutions named in the headline"]

def english_summary(item):
    headline = item["headline"]
    entities = ", ".join(extract_entities(headline))
    lower = headline.lower()
    if any(k in lower for k in ["boston dynamics", "hyundai", "robotics hub", "ownership", "center"]):
        return (
            f"Summary: {entities} point to a more industrial phase for the robotics market: capital, manufacturing capacity, and local hiring are becoming as important as demos. "
            "The story matters because advanced robotics centers can shorten the path from prototype to deployable machines, especially in humanoids, logistics, inspection, and factory automation. "
            "Watch whether the investment leads to new products, customer pilots, supplier expansion, or deeper integration with automotive and AI software groups."
        )
    if any(k in lower for k in ["humanoid", "robot future", "ai center"]):
        return (
            f"Summary: {headline} signals that humanoid and AI-enabled robots are moving from research showcases toward real industrial planning. "
            "The key issue is not only whether a robot can perform impressive tasks, but whether companies can support safe deployment, maintenance, training data, and repeatable unit economics. "
            "Investors and builders should watch partnerships, hiring, factory capacity, and the first commercial use cases that prove robots can work reliably outside controlled demos."
        )
    return (
        f"Summary: {headline} fits the broader AI robotics cycle in which hardware makers, AI labs, and industrial users are trying to turn robotic capability into practical deployment. "
        "The important question is whether this news changes adoption speed, cost curves, supply chains, or customer confidence. "
        "Follow-up signals include pilot programs, production targets, safety approvals, enterprise customers, and whether related suppliers in sensors, actuators, chips, simulation, and fleet software also gain momentum."
    )

def chinese_summary(item):
    headline = item["headline"]
    entities = "、".join(extract_entities(headline))
    if entities == "the companies and institutions named in the headline":
        entities = "相关企业或机构"
    if any(k in headline for k in ["宇树", "具身智能", "产业学院", "机器人", "降价", "现货"]):
        return (
            f"总结：{entities} 相关动态说明，中国 AI 机器人产业正在从单点产品发布，转向教育体系、供应链、渠道和应用场景的同步建设。"
            "如果高校、地方产业园和机器人企业形成更紧密合作，后续人才培养、数据采集、真实场景测试和批量部署都会更快。"
            "这也意味着竞争重点不再只是单台机器人的运动能力，而是能否把硬件、算法、课程、售后和行业客户组织成长期生态。"
            "需要继续观察的是：产品是否真正进入工厂、商业服务和公共场景，价格下降是否带来规模化订单，以及具身智能模型能否和国产硬件形成稳定闭环。"
        )
    return (
        f"总结：{headline} 反映中国 AI 机器人市场仍处在快速扩张阶段，核心变量包括硬件成本、运动控制、视觉感知、具身智能模型和落地场景。"
        "这类新闻的意义不只是单个企业曝光，而是看产业链是否正在形成从研发、教育、制造到应用的完整循环。"
        "如果地方高校、产业园和企业开始共同建设专业、实验室或应用示范，说明行业正在为规模化部署补齐人才和场景。"
        "后续应重点观察量产能力、真实客户、渠道价格、政策支持和与汽车、制造、物流、商业服务等行业的结合速度。"
    )

def japanese_summary(item):
    headline = item["headline"]
    entities = "、".join(extract_entities(headline))
    if entities == "the companies and institutions named in the headline":
        entities = "関係企業・自治体"
    if any(k in headline for k in ["AGRIST", "農業", "収穫", "獣害"]):
        return (
            f"要約：{entities} の動きは、日本のロボット産業が人手不足や農業現場の課題に向けて、より実用的な段階へ進んでいることを示している。"
            "重要なのは、単なる技術展示ではなく、収穫、監視、獣害対策、作業補助といった現場で継続的に使えるかどうかである。"
            "今後は、導入コスト、保守体制、農家や自治体との実証結果、Microsoft など外部 AI 基盤との連携が、商用化の速度を左右する。"
            "特に日本では現場ごとの作業条件が細かいため、ロボット単体の性能だけでなく、運用設計、データ収集、導入後の改善サイクルが競争力になる。"
        )
    if any(k in headline for k in ["ソニー", "アイボ", "aibo"]):
        return (
            f"要約：{entities} に関するニュースは、日本の家庭向けロボット市場が次の転換点に差しかかっていることを示す。"
            "aibo のような製品は、単なる家電ではなく、センサー、クラウド、音声認識、感情表現、長期サポートを含むサービス型ロボットの象徴だった。"
            "今後は、国内販売終了やサービス継続の方針が、消費者向けロボットの収益性、保守負担、次世代製品への投資判断にどう影響するかが焦点になる。"
            "家庭用ロボットは感情価値と継続課金の設計が難しく、次世代では生成 AI、見守り、ヘルスケア、家族コミュニケーションとの統合が重要になる。"
        )
    if any(k in headline for k in ["AIデータセンター", "東電", "孫"]):
        return (
            f"要約：{entities} の話題は、ロボットやフィジカル AI の基盤として、電力、データセンター、計算資源がますます重要になっていることを示している。"
            "日本で AI インフラを整備できるかどうかは、ロボットの学習、シミュレーション、遠隔運用、産業データ活用の競争力に直結する。"
            "今後は、電力制約、投資規模、クラウド事業者との連携、製造業や物流現場での AI ロボット活用がどこまで進むかを見たい。"
            "ロボット産業は本体開発だけでなく、学習用データ、GPU 計算、通信、電力調達まで含めたインフラ競争になりつつある。"
        )
    return (
        f"要約：{headline} は、日本の AI・ロボット産業が研究開発だけでなく、実証、販売、インフラ、現場導入へ広がっていることを示す。"
        "日本市場では、少子高齢化、人手不足、製造業の自動化、農業や物流の省人化が強い需要要因になっている。"
        "今後は、実証実験が商用契約に進むか、国内企業がセンサー、アクチュエータ、制御ソフト、AI 基盤を組み合わせて競争力を出せるかが重要になる。"
        "海外勢との違いを出すには、精密部品、現場改善、保守網、顧客との共同開発を組み合わせた日本型の実装力が問われる。"
    )

def fallback_summary_lines(region, item):
    if region["emoji"] == "🇺🇸":
        return [
            f"  English: {english_summary(item)}",
            f"  中文：总结：这条新闻围绕 {item['headline']}，重点在于美国机器人产业正从演示阶段走向资本投入、产能建设和企业级部署。后续要看相关公司能否把 AI、硬件制造、供应链和真实客户场景结合起来。",
        ]
    if region["emoji"] == "🇨🇳":
        return [
            f"  中文：{chinese_summary(item)}",
            f"  English: This item shows how China's robotics ecosystem is expanding across hardware, embodied AI, education, manufacturing, and commercial deployment. Watch whether pilots turn into repeatable orders and whether lower hardware costs accelerate adoption.",
        ]
    if region["emoji"] == "🇯🇵":
        return [
            f"  日本語：{japanese_summary(item)}",
            f"  中文：总结：这条日本市场新闻围绕 {item['headline']}，重点不是单个标题本身，而是日本 AI/机器人产业在农业、家庭机器人、工业自动化、AI 基础设施或现场实证中的落地进展。后续要看这些项目能否从试验走向持续商业化。",
        ]
    return [f"  English: {english_summary(item)}"]

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
            summary_lines = "\n".join(fallback_summary_lines(region, item))
            parts.append(
                f"- **[{item['date']}] {item['source']} — {item['headline']}**\n"
                f"{summary_lines}\n"
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
            en = jp = zh = src_name = src_url = ""
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
                elif ln.startswith("日本語:") or ln.startswith("日本語："):
                    jp = re.split(r'[：:]', ln, maxsplit=1)[-1].strip()
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
                f'{"<p class=item-jp>" + jp + "</p>" if jp else ""}'
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
