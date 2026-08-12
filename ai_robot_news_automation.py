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
        "queries": [
            '("AI robotics" OR "robotics startup") (US OR America)',
            '("humanoid robot" OR "humanoid robotics") (Tesla OR Optimus OR Figure OR Apptronik OR Agility Robotics)',
            '("Boston Dynamics" OR "Atlas robot" OR "Stretch robot")',
            '("robotics startup" OR "robot automation") (Amazon OR warehouse OR logistics OR factory) US',
            '("physical AI" OR "embodied AI") robotics NVIDIA US',
        ],
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
    {
        "emoji": "🤖",
        "label": "Humanoid Robotics",
        "query": '("humanoid robot" OR "humanoid robotics" OR "embodied AI" OR "bipedal robot")',
        "queries": [
            '"Omakase Robotics" OR "Omakase OS" OR "D1 humanoid" OR "日本 ヒューマノイド ロボット"',
            '"humanoid robot" "Japan" robotics Omakase',
            '"humanoid robot" OR "humanoid robotics" OR "bipedal robot"',
            '"Figure AI" OR "Boston Dynamics Atlas" OR "Tesla Optimus" OR "Agility Robotics" OR "Apptronik Apollo"',
            '"Unitree G1" OR "Agibot" OR "UBTech" OR "Fourier GR-1" humanoid',
        ],
        "hl": "en-US",
        "gl": "US",
        "ceid": "US:en",
        "min_items": 5,
        "exclude_terms": ["fiction", "movie", "anime", "toy"],
    },
]

PROMPT = f"""You are an AI robotics industry news editor. Today is {DATE_STR} ({WEEKDAY_EN}).

Search for the latest AI robotics news. Find 3-5 items for United States, China, and Japan. Also add a final "Humanoid Robotics" section with at least 5 non-duplicate global humanoid robotics items. Total 14-20 items.

RULES:
1. Prioritize last 24 hours. Expand only to the past 3 days if needed. NEVER use older items.
2. NEVER say sorry, unable to find, or anything similar. FORBIDDEN.
3. Each item must have: date, company name, a substantial summary, and source publication name.
4. Japan section must cover Japan's domestic AI/robotics industry only. Exclude China/Unitree stories merely reported in Japanese.
5. Humanoid Robotics section must cover embodied humanoid robot news globally. The first Humanoid Robotics item must be reserved for Japan's humanoid robotics industry and OmakaseRobotics/Omakase OS/D1 humanoid if any recent item is available.
6. Do NOT include any URLs in your response. I will add them separately.

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

## 🤖 Humanoid Robotics

- **[{DATE_STR}] Company Name — 中文事件概要**
  English: Summary in about 400 characters, covering what happened, why it matters, and what to watch next.
  中文：约300字中文总结，说明事件、产业意义和后续观察点。
  📰 Source Publication Name

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
        scoped_query = query
        if region["label"] == "日本 / Japan":
            scoped_query = f"{query} -中国 -China -Unitree -ユニツリー"
        params = {
            "q": f"{scoped_query} when:3d",
            "hl": region["hl"],
            "gl": region["gl"],
            "ceid": region["ceid"],
        }
        url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                xml = response.read()
        except Exception as ex:
            print(f"   RSS query failed: {query[:70]}... ({ex})")
            continue

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

def fetch_humanoid_items(region, limit=5):
    priority_region = {
        **region,
        "queries": [
            '"Omakase Robotics" OR "Omakase OS" OR "D1 humanoid"',
            '"Omakase Robotics" humanoid robot Japan',
            '"日本" "ヒューマノイド" "ロボット" "Omakase"',
            '"Japan" "humanoid robot" "Omakase"',
            '"日本" "ヒューマノイド" "ロボット"',
        ],
        "hl": "ja",
        "gl": "JP",
        "ceid": "JP:ja",
        "exclude_terms": [],
    }
    priority = fetch_rss_items(priority_region, limit=1)
    global_items = fetch_rss_items(region, limit=limit + 4)
    out = []
    seen = set()
    for item in priority + global_items:
        key = re.sub(r"\W+", "", item["headline"].lower())[:90]
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
        if len(out) >= limit:
            break
    return out

def extract_entities(headline):
    names = [
        "Boston Dynamics", "Hyundai", "Tesla", "Figure", "NVIDIA", "Amazon", "Microsoft", "Google",
        "Unitree", "宇树", "优必选", "UBTech", "小鹏", "华为", "阿里巴巴", "腾讯", "百度",
        "AGRIST", "Sony", "ソニー", "aibo", "ファナック", "安川電機", "Telexistence", "SoftBank", "GMO", "Toyota", "Honda",
    ]
    found = [name for name in names if name.lower() in headline.lower()]
    return found[:4] or ["the companies and institutions named in the headline"]

def short_event(headline, limit=90):
    clean = re.sub(r"\s+", " ", headline).strip()
    return clean if len(clean) <= limit else clean[:limit].rstrip() + "..."

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
    event = short_event(headline)
    points = []
    if any(k in headline for k in ["宇树", "Unitree"]):
        points.append("宇树相关动态会直接影响中国人形机器人硬件价格、海外关注度和开发者生态")
    if any(k in headline for k in ["具身智能", "人形", " humanoid", "机器人"]):
        points.append("具身智能或人形机器人线索需要看运动控制、感知模型和真实任务执行是否同步进步")
    if any(k in headline for k in ["产业学院", "高校", "大学", "教育", "人才"]):
        points.append("教育和产业学院相关内容说明行业正在补人才、课程、实验场景和应用数据")
    if any(k in headline for k in ["降价", "现货", "发布", "量产", "开售", "价格"]):
        points.append("价格、现货或量产信息要观察是否带来真实订单，而不是短期曝光")
    if any(k in headline for k in ["工厂", "物流", "商业", "巡检", "服务"]):
        points.append("工厂、物流或商业服务场景比单纯演示更能验证 ROI 和维护能力")
    if not points:
        points.append("这条新闻反映中国 AI 机器人市场在硬件、算法、供应链或应用场景上的推进")
    if any(k in headline for k in ["宇树", "具身智能", "产业学院", "机器人", "降价", "现货"]):
        return (
            f"总结：{entities} 是这条中国市场新闻的主要观察对象，具体事件是「{event}」。"
            + "；".join(points[:3])
            + "。后续需要观察真实订单、交付节奏、售后能力、开发者生态和行业客户是否跟上，避免只停留在发布会或短期流量。"
        )
    return (
        f"总结：这条新闻的具体事件是「{event}」。"
        + "；".join(points[:3])
        + "。判断价值不在于标题热度，而在于它是否改变硬件成本、运动控制、视觉感知、具身智能模型、客户场景或供应链协作。"
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

def us_robotics_chinese_summary(item):
    headline = item["headline"]
    lower = headline.lower()
    entities = "、".join(extract_entities(headline))
    if entities == "the companies and institutions named in the headline":
        entities = "标题中的相关企业或机构"
    event = short_event(headline)
    points = []
    if any(k in lower for k in ["funding", "raises", "investment", "valuation", "ipo"]):
        points.append("资本事件说明美国机器人公司仍在为量产、人才和长期客户验证筹集资源")
    if any(k in lower for k in ["factory", "manufacturing", "warehouse", "logistics", "amazon"]):
        points.append("制造、仓储或物流场景意味着机器人正在接近可计算 ROI 的企业级部署")
    if any(k in lower for k in ["humanoid", "boston dynamics", "figure", "tesla", "optimus", "agility", "apptronik"]):
        points.append("人形机器人相关内容要重点看全身控制、续航、安全和真实任务完成率")
    if any(k in lower for k in ["nvidia", "ai", "model", "simulation", "vision"]):
        points.append("AI 模型、仿真和视觉能力会影响机器人从固定流程走向更复杂环境的速度")
    if not points:
        points.append("这条消息反映美国机器人产业在产品、客户、供应链或应用场景上的推进")
    return (
        f"总结：{entities} 是这条美国市场新闻的主要观察对象，具体事件是「{event}」。"
        + "；".join(points[:3])
        + "。后续要看它是否带来明确客户、试点扩大、量产节奏、成本下降或供应链协同，而不是只停留在概念展示。"
    )

def japan_robotics_chinese_summary(item):
    headline = item["headline"]
    entities = "、".join(extract_entities(headline))
    if entities == "the companies and institutions named in the headline":
        entities = "日本相关企业、自治体或研究机构"
    event = short_event(headline)
    points = []
    if any(k in headline for k in ["農業", "収穫", "獣害", "AGRIST"]):
        points.append("农业和现场作业场景直接对应日本人手不足，重点是能否降低持续运营成本")
    if any(k in headline for k in ["ソニー", "aibo", "アイボ"]):
        points.append("家庭或陪伴机器人消息要看服务周期、维护成本和生成 AI 时代的产品更新")
    if any(k in headline for k in ["ファナック", "安川", "工場", "製造"]):
        points.append("工业自动化消息更接近日本传统优势，重点是 AI 是否提升柔性生产能力")
    if any(k in headline for k in ["ヒューマノイド", "人型", "Omakase", "ロボット"]):
        points.append("人形或服务机器人线索要看安全合规、现场流程接入和日本本土客户验证")
    if not points:
        points.append("这条新闻体现日本机器人产业从研发展示走向现场验证、销售或基础设施建设")
    return (
        f"总结：{entities} 是这条日本市场新闻的主要观察对象，具体事件是「{event}」。"
        + "；".join(points[:3])
        + "。后续应关注试点是否转成商用合同、保守维护体系是否成立，以及日本企业能否把精密制造、现场改善和 AI 软件结合起来。"
    )

def humanoid_event_points(headline):
    lower = headline.lower()
    en, zh = [], []
    if any(k in lower for k in ["omakase", "d1", "japan", "日本", "ヒューマノイド"]):
        en.append("Japan is relevant because humanoid deployment there is tied to labor shortages, service work, safety rules, and local operating software")
        zh.append("日本线索的重点在于人手不足、服务业现场、安全合规和本土机器人操作系统能否结合起来")
    if any(k in lower for k in ["hospital", "airport", "warehouse", "factory", "logistics", "retail", "hotel", "hospitality"]):
        en.append("the headline points to field deployment rather than a lab demo, so reliability and workflow integration are the main tests")
        zh.append("标题指向真实场景部署，而不是单纯实验室演示，因此可靠性、流程接入和现场维护是关键")
    if any(k in lower for k in ["tesla", "optimus"]):
        en.append("Tesla Optimus news matters because manufacturing scale and internal factory use could change cost expectations")
        zh.append("Tesla Optimus 的意义在于制造规模和内部工厂应用可能改变人形机器人成本预期")
    if any(k in lower for k in ["figure", "apptronik", "agility", "boston dynamics", "atlas"]):
        en.append("US developers are competing on whole-body control, enterprise pilots, and credible commercialization timelines")
        zh.append("美国开发商竞争重点在全身控制、企业试点和可验证的商业化时间表")
    if any(k in lower for k in ["unitree", "ubtech", "agibot", "fourier", "china", "中国", "宇树", "优必选", "智元"]):
        en.append("China-linked humanoid news is important for price pressure, fast iteration, and component supply-chain depth")
        zh.append("中国相关人形机器人新闻主要影响价格压力、迭代速度和零部件供应链深度")
    if any(k in lower for k in ["funding", "raises", "investment", "valuation", "ipo"]):
        en.append("capital-market activity shows investors are still underwriting a long deployment cycle")
        zh.append("融资或估值新闻说明资本仍在为人形机器人的长期部署周期买单")
    if any(k in lower for k in ["release", "launch", "unveil", "announces", "sales", "preorder", "販売"]):
        en.append("a launch or sales signal should be judged by order quality, support capacity, and repeatable use cases")
        zh.append("发布或销售消息需要看订单质量、交付支持能力和可重复使用场景")
    if not en:
        en.append("the item should be read as a signal of where humanoid robotics is moving from demos toward useful work")
        zh.append("这条消息应被视为人形机器人从演示走向有用劳动的产业信号")
    return en[:4], zh[:4]

def humanoid_summary_lines(item, first=False):
    headline = item["headline"]
    entities = ", ".join(extract_entities(headline))
    if entities == "the companies and institutions named in the headline":
        entities = "the companies named in the headline"
    en_points, zh_points = humanoid_event_points(headline)
    prefix = "Priority Japan/Omakase item" if first else "Humanoid robotics item"
    en = (
        f"Summary: {prefix}: {entities}. "
        + " ".join(point[0].upper() + point[1:] + "." for point in en_points)
        + " Watch whether the news leads to paid pilots, repeat deployments, hardware availability, safety approvals, or stronger software integration across perception, planning, speech, and remote operation."
    )
    zh = (
        "总结："
        + ("第一条保留给日本人形机器人产业与 OmakaseRobotics 相关动向。" if first else "")
        + f"{headline} 的核心不是标题热度，而是它对应的人形机器人商业化阶段。"
        + "；".join(zh_points)
        + "。后续要看是否出现付费试点、连续部署、硬件供货、现场安全认证，以及感知、规划、语音交互和远程运维软件是否真正进入客户流程。"
    )
    return [f"  English: {en}", f"  中文：{zh}"]

def fallback_summary_lines(region, item):
    if region["label"] == "Humanoid Robotics":
        return humanoid_summary_lines(item)
    if region["emoji"] == "🇺🇸":
        return [
            f"  English: {english_summary(item)}",
            f"  中文：{us_robotics_chinese_summary(item)}",
        ]
    if region["emoji"] == "🇨🇳":
        return [
            f"  中文：{chinese_summary(item)}",
            f"  English: This item shows how China's robotics ecosystem is expanding across hardware, embodied AI, education, manufacturing, and commercial deployment. Watch whether pilots turn into repeatable orders and whether lower hardware costs accelerate adoption.",
        ]
    if region["emoji"] == "🇯🇵":
        return [
            f"  日本語：{japanese_summary(item)}",
            f"  中文：{japan_robotics_chinese_summary(item)}",
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
            items = fetch_humanoid_items(region, region.get("min_items", 5)) if region["label"] == "Humanoid Robotics" else fetch_rss_items(region)
        except Exception as e:
            print(f"   RSS error for {region['label']}: {e}")
            items = []

        parts.append(f"\n## {region['emoji']} {region['label']}\n")
        if not items:
            parts.append(f"- **[{DATE_STR}] No RSS result — 暂无可验证 RSS 新闻**\n  English: Google News RSS returned no recent result for this region.\n  中文：本地区暂未抓取到可验证的 Google News RSS 结果。\n  📰 Google News")
            continue

        for idx, item in enumerate(items):
            total += 1
            if region["label"] == "Humanoid Robotics":
                summary_lines = "\n".join(humanoid_summary_lines(item, first=(idx == 0)))
            else:
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
            for e in ["🇺🇸","🇨🇳","🇯🇵","🤖"]:
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
