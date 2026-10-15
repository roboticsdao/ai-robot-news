#!/usr/bin/env python3
import html
import os, subprocess, re, sys, time, json, unicodedata, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from difflib import SequenceMatcher
from datetime import datetime, timezone, timedelta
from pathlib import Path
from edition_health import write_feed

from article_summaries import (
    deduplicate_summaries,
    enrich_articles,
    fetch_rss_bytes,
    remove_repeated_summary_sentences,
    summarize_articles,
    summary_quality_issues,
)

LOCAL_TZ = timezone(timedelta(hours=9))
TODAY = datetime.now(LOCAL_TZ)
DATE_STR = TODAY.strftime("%Y.%m.%d")
TIME_STR = TODAY.strftime("%H:%M")
PRIMARY_WINDOW_DAYS = 7
MAX_WINDOW_DAYS = 14
MIN_DAILY_ITEMS = 5
DAILY_ITEM_TARGET = 8
CUTOFF_DATE = (TODAY - timedelta(days=MAX_WINDOW_DAYS)).date()
WEEKDAY_MAP = {0:"月",1:"火",2:"水",3:"木",4:"金",5:"土",6:"日"}
WEEKDAY_EN = TODAY.strftime("%A")
WEEKDAY_JP = WEEKDAY_MAP[TODAY.weekday()]
IS_CI = os.environ.get("CI","") == "true"
OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / f"Dexterous_Hand_News_{TODAY.strftime('%Y%m%d')}.md"
HISTORY_FILE = OUTPUT_DIR / "history.json"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY","")
PAGE_URL = "https://roboticsdao.github.io/ai-robot-news/dexterous-hand-news/latest.html"

REGIONS = [
    {
        "emoji": "🇯🇵",
        "label": "日本 / Japan",
        "query": "ロボットハンド 多指 触覚センサー",
        "queries": [
            "ロボットハンド 多指ハンド 日本",
            "触覚センサー ロボット 把持 日本",
            "器用なロボットハンド 開発",
            "エンドエフェクタ ロボット 日本",
            "ヒューマノイド ハンド 日本企業",
        ],
        "hl": "ja",
        "gl": "JP",
        "ceid": "JP:ja",
        "min_items": 3,
        "exclude_terms": ["義手", "手術", "医療のみ", "中国製の紹介"],
    },
    {
        "emoji": "🇺🇸",
        "label": "美国 / United States",
        "query": '("dexterous robot hand" OR "robotic hand") (US OR America)',
        "queries": [
            '"dexterous robot hand" robotics',
            '"robotic hand" tactile manipulation humanoid',
            '"tactile sensor" robot hand manipulation',
            '"end effector" dexterous robotics startup',
            'robot hand teleoperation embodied AI',
        ],
        "hl": "en-US",
        "gl": "US",
        "ceid": "US:en",
        "min_items": 3,
        "exclude_terms": ["prosthetic", "surgery", "medical device only"],
    },
    {
        "emoji": "🇨🇳",
        "label": "中国 / China",
        "query": "机器人 灵巧手 触觉传感",
        "queries": [
            "人形机器人 灵巧手 最新",
            "机器人 灵巧手 量产",
            "触觉传感器 机器人手 抓取",
            "具身智能 灵巧手 企业",
            "机器人 末端执行器 遥操作",
        ],
        "hl": "zh-CN",
        "gl": "CN",
        "ceid": "CN:zh-Hans",
        "min_items": 3,
        "exclude_terms": ["假肢", "手术", "纯医疗"],
    },
    {
        "emoji": "🔬",
        "label": "全球研究与产业 / Global Research & Industry",
        "query": '("dexterous manipulation" OR "robot hand" OR "tactile sensing") robotics',
        "queries": [
            '"dexterous manipulation" robot research',
            '"tactile sensing" robotic hand research',
            '"visuotactile" robot manipulation',
            '"robot gripper" AI manipulation research',
            '"dexterous hand" humanoid industry',
        ],
        "hl": "en-US",
        "gl": "US",
        "ceid": "US:en",
        "min_items": 3,
        "exclude_terms": ["prosthetic", "surgery", "movie", "anime", "toy"],
    },
]

PROMPT = f"""Dexterous Hand News | {DATE_STR}. Summaries are produced from each article body and contain only attributed facts."""

CSS = """:root{color-scheme:light;--bg:#fff;--fg:#1a1a1a;--fg2:#6b6b6f;--fg3:#9a9a9e;--border:#d4d4d4;--border2:#e8e8e8;--serif:Georgia,"Times New Roman",serif;--sans:-apple-system,BlinkMacSystemFont,"Helvetica Neue",sans-serif;--link:#1a6ed8;--hover:#f5f5f5;--menu-bg:#fff;--menu-shadow:rgba(0,0,0,0.12)}
:root[data-theme="dark"]{color-scheme:dark;--bg:#1a1a1a;--fg:#e2e2e2;--fg2:#a0a0a0;--fg3:#707070;--border:#444;--border2:#333;--link:#6db3f8;--hover:#2a2a2a;--menu-bg:#252525;--menu-shadow:rgba(0,0,0,0.4)}
@media(prefers-color-scheme:dark){:root:not([data-theme]){color-scheme:dark;--bg:#1a1a1a;--fg:#e2e2e2;--fg2:#a0a0a0;--fg3:#707070;--border:#444;--border2:#333;--link:#6db3f8;--hover:#2a2a2a;--menu-bg:#252525;--menu-shadow:rgba(0,0,0,0.4)}}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:var(--sans);margin:0 auto;padding:28px 0;background:var(--bg);color:var(--fg);line-height:1.75;font-size:15px;-webkit-font-smoothing:antialiased;width:calc(100vw - 48px)}
@media(max-width:760px){body{width:calc(100vw - 32px);padding:20px 0}}
.top-bar{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}
.top-actions{display:flex;align-items:center;gap:10px}.updated-at{font-size:11px;color:var(--fg3);white-space:nowrap}.theme-btn{width:32px;height:32px;display:grid;place-items:center;border:1px solid var(--border);border-radius:8px;background:var(--menu-bg);color:var(--fg2);font:18px/1 var(--sans);cursor:pointer}.theme-btn:hover{background:var(--hover);color:var(--fg)}.theme-btn:focus-visible{outline:2px solid var(--link);outline-offset:2px}
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

THEME_JS = '''<script>(function(){var root=document.documentElement,key="news-theme",media=window.matchMedia("(prefers-color-scheme: dark)");try{var saved=localStorage.getItem(key);if(saved==="light"||saved==="dark")root.dataset.theme=saved}catch(e){}function current(){return root.dataset.theme||(media.matches?"dark":"light")}function setup(){var button=document.getElementById("themeBtn"),icon=document.getElementById("themeIcon");if(!button||!icon)return;function render(){var dark=current()==="dark";icon.textContent=dark?"☀":"◐";button.title=dark?"切换到白色背景":"切换到黑色背景";button.setAttribute("aria-label",button.title);button.setAttribute("aria-pressed",dark?"true":"false")}button.onclick=function(){var next=current()==="dark"?"light":"dark";root.dataset.theme=next;try{localStorage.setItem(key,next)}catch(e){}render()};if(media.addEventListener)media.addEventListener("change",render);render()}if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",setup);else setup()})();</script>'''

def generate_digest():
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

def robotics_topic(headline):
    lower = headline.lower()
    if re.search(r"\d+(?:\.\d+)?%", lower) and any(term in lower for term in ["humanoid", "人形", "ヒューマノイド"]):
        return "market"
    rules = [
        ("regulation", ["regulat", "resolution", "law", "policy", "safety", "certif", "規制", "安全", "法案", "标准"]),
        ("market", ["shipment", "sales", "market share", "market size", "cagr", "出货", "销量", "市場規模", "占比", "份额"]),
        ("finance", ["funding", "raises", "investment", "investor", "valuation", "ipo", "fund", "融资", "投资", "上市", "估值", "調達"]),
        ("deployment", ["pilot", "trial", "deploy", "poc", "hospital", "factory", "warehouse", "shipbuilding", "上岗", "実証", "導入", "病院", "工場"]),
        ("product", ["launch", "release", "unveil", "debut", "new robot", "preorder", "販売", "発売", "公開", "发布", "开售", "新品"]),
        ("research", ["research", "model", "platform", "data", "laboratory", "lab", "chip", "研究", "データ", "実験室", "模型", "算法", "数据"]),
        ("partnership", ["partner", "collabor", "alliance", "ecosystem", "council", "協議会", "連携", "合作", "生态", "产业链"]),
        ("people", ["advisor", "appoint", "hire", "ownership", "顧問", "就任", "招聘", "人才", "学院", "ロボコン"]),
        ("manufacturing", ["mass production", "manufactur", "supply chain", "delivery", "量产", "交付", "製造", "生産", "供应链"]),
        ("consumer", ["review", "home robot", "companion", "aibo", "friends", "家庭", "陪伴", "レビュー", "癒"]),
    ]
    for topic, keywords in rules:
        if any(keyword in lower for keyword in keywords):
            return topic
    return "general"


def is_relevant_robotics_item(region, headline):
    lower = headline.lower()
    hand_terms = [
        "dexterous hand", "dexterous manipulation", "robot hand", "robotic hand", "tactile sensor",
        "tactile sensing", "visuotactile", "gripper", "end effector", "teleoperation", "in-hand",
        "ロボットハンド", "多指ハンド", "触覚センサ", "触覚センサー", "把持", "エンドエフェクタ",
        "灵巧手", "机器人手", "机械手", "触觉传感", "末端执行器", "抓取", "仿生手", "遥操作",
    ]
    if not any(term in lower for term in hand_terms):
        return False
    if region["emoji"] == "🇺🇸":
        return not any(term in lower for term in ["中国", "日本語", "国内企業"])
    if region["emoji"] == "🇯🇵":
        return not any(term in lower for term in ["中国", "china", "韩国", "korea", "unitree", "宇树"])
    if region["emoji"] == "🇨🇳":
        return not any(term in lower for term in ["日本", "米国企業"])
    return True

def robotics_story_bucket(headline):
    topic = robotics_topic(headline)
    entities = extract_entities(headline)
    entity = entities[0] if entities and entities[0] != "the companies and institutions named in the headline" else "general"
    return f"{topic}:{entity.lower()}", topic

def robotics_event_signature(headline):
    lower = headline.lower()
    percentages = re.findall(r"\d+(?:\.\d+)?%", lower)
    if percentages:
        return f"{robotics_topic(headline)}:{percentages[0]}"
    return ""

def has_recent_content(text):
    dates = re.findall(r'-\s*\*\*\[(\d{4}[\.\-/]\d{2}[\.\-/]\d{2})\]', text or "")
    if not dates:
        return False
    return all((parsed := parse_item_date(d)) is not None and CUTOFF_DATE <= parsed <= TODAY.date() for d in dates)

def section_item_counts(text):
    counts = {}
    current = None
    for line in (text or "").splitlines():
        clean = line.strip()
        if clean.startswith("## "):
            current = clean[3:].strip()
            counts[current] = 0
        elif current and clean.startswith("- **"):
            counts[current] += 1
    return counts

def has_required_content(text):
    if not has_recent_content(text):
        return False
    counts = section_item_counts(text)
    return any("🌍" in heading and count >= MIN_DAILY_ITEMS for heading, count in counts.items())

def digest_summary_records(text):
    records = []
    starts = list(re.finditer(r"(?m)^-\s*\*\*\[[^\]]+\]\s*(.+?)\*\*", text or ""))
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        block = text[match.end():end]
        title = match.group(1).strip()
        for line in block.splitlines():
            clean = line.strip()
            if re.match(r"^(English|En|中文|日本語)\s*[：:]", clean, re.I):
                records.append((title, re.sub(r"^(English|En|中文|日本語)\s*[：:]\s*", "", clean, flags=re.I)))
    return records

def digest_quality_issues(text):
    records = digest_summary_records(text)
    issues = []
    sentence_owner = {}
    for title, summary in records:
        for sentence in re.split(r"(?<=[.!?。！？])\s*", summary):
            normalized = re.sub(r"\s+", " ", sentence).strip().lower()
            if len(normalized) < 45:
                continue
            previous = sentence_owner.get(normalized)
            if previous and previous != title:
                issues.append(f'repeated sentence in "{previous}" and "{title}"')
            else:
                sentence_owner[normalized] = title
    for i, (title_a, summary_a) in enumerate(records):
        lang_a = "cjk" if re.search(r"[\u3040-\u30ff\u3400-\u9fff]", summary_a) else "en"
        norm_a = re.sub(r"\s+", "", summary_a).lower()
        for title_b, summary_b in records[i + 1:]:
            if title_a == title_b:
                continue
            lang_b = "cjk" if re.search(r"[\u3040-\u30ff\u3400-\u9fff]", summary_b) else "en"
            if lang_a != lang_b:
                continue
            norm_b = re.sub(r"\s+", "", summary_b).lower()
            ratio = SequenceMatcher(None, norm_a, norm_b).ratio()
            if ratio >= 0.88:
                issues.append(f'highly similar summaries ({ratio:.0%}) in "{title_a}" and "{title_b}"')
    return issues

def validate_digest_quality(text):
    issues = digest_quality_issues(text)
    if issues:
        print("   Summary quality check failed:")
        for issue in issues[:8]:
            print(f"   - {issue}")
        return False
    return True

def canonical_headline(headline):
    clean = unicodedata.normalize("NFKC", headline or "").lower()
    clean = re.sub(r"\s*[（(][^()（）]{2,40}[）)]\s*$", "", clean)
    clean = re.sub(r"[^\w\u3040-\u30ff\u3400-\u9fff]+", "", clean)
    return clean

def headline_tokens(headline):
    stop = {"the", "and", "for", "with", "from", "into", "that", "this", "its", "due", "new", "by", "at", "to", "in", "of", "on", "a", "an"}
    tokens = []
    for token in re.findall(r"[a-z0-9]+", unicodedata.normalize("NFKC", headline or "").lower()):
        if token in stop or len(token) < 3:
            continue
        if token.startswith("invest"):
            token = "invest"
        elif token.endswith("s") and len(token) > 4:
            token = token[:-1]
        tokens.append(token)
    return set(tokens)

def duplicate_story(headline, other_headlines):
    canonical = canonical_headline(headline)
    if not canonical:
        return False
    entities = {name.lower() for name in extract_entities(headline) if not name.startswith("the companies")}
    tokens = headline_tokens(headline)
    dexterous = any(term in headline.lower() for term in ["dexterous", "robot hand", "ロボットハンド", "多指ハンド", "灵巧手", "机器人手"])
    for other in other_headlines:
        other_canonical = canonical_headline(other)
        if canonical == other_canonical:
            return True
        if min(len(canonical), len(other_canonical)) >= 24 and SequenceMatcher(None, canonical, other_canonical).ratio() >= 0.78:
            return True
        other_tokens = headline_tokens(other)
        shared_tokens = tokens & other_tokens
        token_union = tokens | other_tokens
        overlap = len(shared_tokens) / len(token_union) if token_union else 0
        if (len(shared_tokens) >= 4 and overlap >= 0.35) or (len(shared_tokens) >= 5 and overlap >= 0.30):
            return True
        other_entities = {name.lower() for name in extract_entities(other) if not name.startswith("the companies")}
        other_dexterous = any(term in other.lower() for term in ["dexterous", "robot hand", "ロボットハンド", "多指ハンド", "灵巧手", "机器人手"])
        if dexterous and other_dexterous and len(entities & other_entities) >= 2:
            return True
    return False

def fetch_rss_items(region, limit=5, exclude_headlines=None, window_days=PRIMARY_WINDOW_DAYS):
    items = []
    seen = set()
    exclude_terms = region.get("exclude_terms", [])
    queries = region.get("queries") or [region["query"]]
    for query in queries:
        query_added = 0
        scoped_query = query
        if region["label"] == "日本 / Japan":
            scoped_query = f"{query} -中国 -China -Unitree -ユニツリー"
        params = {
            "q": f"{scoped_query} when:{window_days}d",
            "hl": region["hl"],
            "gl": region["gl"],
            "ceid": region["ceid"],
        }
        url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            xml = fetch_rss_bytes(req)
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
            if not is_relevant_robotics_item(region, headline):
                continue
            seen.add(headline.lower())
            try:
                dt = datetime.strptime(published, "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=timezone.utc).astimezone(LOCAL_TZ)
                date = dt.strftime("%Y.%m.%d")
            except Exception:
                continue
            window_cutoff = (TODAY - timedelta(days=window_days)).date()
            if parse_item_date(date) < window_cutoff:
                continue
            items.append({"date": date, "headline": headline, "source": source, "link": link, "dt": dt})
            query_added += 1
            query_cap = max(limit * 2, 8) if len(queries) == 1 else max(2, min(limit, 4))
            if query_added >= query_cap:
                break
    ordered = sorted(items, key=lambda item: item.get("dt", TODAY), reverse=True)
    excluded = list(exclude_headlines or [])
    selected, bucket_counts, topic_counts, source_counts, event_signatures = [], {}, {}, {}, set()
    for item in ordered:
        if duplicate_story(item["headline"], excluded + [selected_item["headline"] for selected_item in selected]):
            continue
        bucket, topic = robotics_story_bucket(item["headline"])
        event_signature = robotics_event_signature(item["headline"])
        topic_limit = 2
        source_key = item["source"].lower()
        if (event_signature and event_signature in event_signatures) or bucket_counts.get(bucket, 0) >= 1 or topic_counts.get(topic, 0) >= topic_limit or source_counts.get(source_key, 0) >= 2:
            continue
        selected.append(item)
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
        topic_counts[topic] = topic_counts.get(topic, 0) + 1
        source_counts[source_key] = source_counts.get(source_key, 0) + 1
        if event_signature:
            event_signatures.add(event_signature)
        if len(selected) >= limit:
            return selected
    for item in ordered:
        event_signature = robotics_event_signature(item["headline"])
        if item not in selected and not duplicate_story(item["headline"], excluded + [selected_item["headline"] for selected_item in selected]) and (not event_signature or event_signature not in event_signatures):
            selected.append(item)
            if event_signature:
                event_signatures.add(event_signature)
        if len(selected) >= limit:
            break
    return selected

def fetch_humanoid_items(region, limit=5, exclude_headlines=None):
    omakase_region = {
        **region,
        "queries": [
            '"Omakase Robotics" OR "Omakase OS" OR "D1 humanoid"',
            '"Omakase Robotics" humanoid robot Japan',
        ],
        "hl": "ja",
        "gl": "JP",
        "ceid": "JP:ja",
        "exclude_terms": [],
    }
    japan_region = {
        **omakase_region,
        "queries": [
            '"日本" "ヒューマノイド" "ロボット" "Omakase"',
            '"Japan" "humanoid robot" "Omakase"',
            '"日本" "ヒューマノイド" "ロボット"',
        ],
    }
    excluded = list(exclude_headlines or [])
    priority = fetch_rss_items(omakase_region, limit=1, exclude_headlines=excluded) or fetch_rss_items(japan_region, limit=1, exclude_headlines=excluded)
    priority_headlines = [item["headline"] for item in priority]
    global_items = fetch_rss_items(region, limit=limit + 8, exclude_headlines=excluded + priority_headlines)
    out = []
    seen = set()
    for item in priority + global_items:
        key = canonical_headline(item["headline"])
        if key in seen or duplicate_story(item["headline"], [existing["headline"] for existing in out]):
            continue
        seen.add(key)
        out.append(item)
        if len(out) >= limit:
            break
    return out

def extract_entities(headline):
    names = [
        "Shadow Robot", "Sanctuary AI", "Tesla", "Figure", "Apptronik", "Agility Robotics", "Meta", "NVIDIA", "Google DeepMind",
        "Unitree", "宇树", "优必选", "UBTech", "智元", "傅利叶", "PaXini", "帕西尼", "灵心巧手", "因时机器人",
        "Toyota", "Honda", "川崎重工", "ファナック", "安川電機", "オムロン", "早稲田大学", "産総研",
    ]
    found = [name for name in names if name.lower() in headline.lower()]
    return found[:4] or ["the companies and institutions named in the headline"]











def generate_digest_from_rss():
    parts = [
        f"# 🖐 Dexterous Hand News | {DATE_STR}（{WEEKDAY_JP}曜日 / {WEEKDAY_EN}）",
        "",
        "> ⚠️ 本日报收录全球机器人灵巧手新闻，优先选择7天内内容，数量不足时最多回溯14天；摘要仅压缩原文事实，不添加商业判断或预测。",
        "",
        "---",
    ]

    collected_items = []
    global_headlines = []
    for region in REGIONS:
        print(f"   Search feed: {region['emoji']} {region['label']}")
        feed_target = 3
        candidate_limit = feed_target + 8
        try:
            candidates = fetch_rss_items(
                region,
                candidate_limit,
                exclude_headlines=global_headlines,
                window_days=PRIMARY_WINDOW_DAYS,
            )
            for item in candidates:
                item["summary_language"] = "Japanese" if region["emoji"] == "🇯🇵" else "Chinese" if region["emoji"] == "🇨🇳" else "English"
                item["region_label"] = region["label"]
            items = enrich_articles(candidates)
            if len(items) < feed_target:
                excluded = global_headlines + [item["headline"] for item in candidates]
                older_candidates = fetch_rss_items(
                    region,
                    candidate_limit + 8,
                    exclude_headlines=excluded,
                    window_days=MAX_WINDOW_DAYS,
                )
                for item in older_candidates:
                    item["summary_language"] = "Japanese" if region["emoji"] == "🇯🇵" else "Chinese" if region["emoji"] == "🇨🇳" else "English"
                    item["region_label"] = region["label"]
                items.extend(enrich_articles(older_candidates))
            items = items[:feed_target + 2]
            print(f"   Readable full-text items: {len(items)}")
        except Exception as e:
            print(f"   Article fetch error for {region['label']}: {e}")
            items = []
        global_headlines.extend(item["headline"] for item in items)
        collected_items.extend(items)

    collected_items.sort(key=lambda item: item.get("dt", TODAY), reverse=True)
    unique_items = []
    for item in collected_items:
        if duplicate_story(item["headline"], [existing["headline"] for existing in unique_items]):
            continue
        unique_items.append(item)
        if len(unique_items) >= DAILY_ITEM_TARGET + 4:
            break

    summarized = summarize_articles(unique_items, GEMINI_API_KEY)
    summarized, removed = deduplicate_summaries(summarized)
    if removed:
        print(f"   Removed {len(removed)} duplicate summaries")
    summarized, sentence_repairs = remove_repeated_summary_sentences(summarized)
    if sentence_repairs:
        print(f"   Repaired {len(sentence_repairs)} repeated summary sentences")
    issues = summary_quality_issues(summarized)
    if issues:
        raise RuntimeError("; ".join(issues[:5]))
    summarized.sort(key=lambda item: item.get("dt", TODAY), reverse=True)
    summarized = summarized[:DAILY_ITEM_TARGET]
    total = 0
    parts.append("\n## 🌍 全球灵巧手 / Global Dexterous Hands\n")
    for item in summarized:
        total += 1
        if item["summary_language"] == "Japanese":
            local_line = f"  日本語：{item['local_summary']}\n"
        elif item["summary_language"] == "Chinese":
            local_line = ""
        else:
            local_line = f"  English: {item['local_summary']}\n"
        zh = item.get("zh_summary", "")
        zh_line = f"  中文：总结：{zh}\n" if zh else ""
        parts.append(
            f"- **[{item['date']}] {item['source']} — {item['headline']}**\n"
            f"{local_line}{zh_line}"
            f"  📰 [{item['source']}]({item['link']})"
        )

    if total < MIN_DAILY_ITEMS:
        raise RuntimeError("Fewer than five verified dexterous hand articles; preserving the previous edition")
    write_feed(OUTPUT_DIR, summarized, "hand", TODAY, {"Global": MIN_DAILY_ITEMS})
    parts.append(f"\n---\n※Dexterous Hand News Digest | {DATE_STR} | full-text items: {total}")
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
            for e in ["🌍","🇯🇵","🇺🇸","🇨🇳","🔬"]:
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
        discl = "⚠ 本日报收录全球机器人灵巧手新闻，优先选择7天内内容，数量不足时最多回溯14天。"

    return f'''<!DOCTYPE html>
<html lang="zh"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
		<title>Dexterous Hand News | {DATE_STR}</title><style>{CSS}</style>{THEME_JS}</head><body>
	<div class="top-bar"><div class="history-wrap"><button class="history-btn" id="historyBtn"><svg viewBox="0 0 16 16"><path d="M8 1a7 7 0 1 0 0 14A7 7 0 0 0 8 1zm0 12.5A5.5 5.5 0 1 1 8 2.5a5.5 5.5 0 0 1 0 11zM8.5 4h-1v4.5l3.5 2 .5-.87-3-1.75V4z"/></svg>历史记录</button><div class="history-panel" id="historyPanel"><h3>📅 刷新记录</h3><div id="historyList"></div></div></div><div class="top-actions"><a href="../hub/#hand" style="font-size:12px;color:var(--link);white-space:nowrap">产业图谱</a><div class="updated-at">更新于 {TIME_STR} JST</div><button class="theme-btn" id="themeBtn" type="button"><span id="themeIcon" aria-hidden="true">◐</span></button></div></div>
	<div class="masthead"><h1>Dexterous Hand News</h1><div class="date">{DATE_STR} — {WEEKDAY_EN} / {WEEKDAY_JP}曜日</div></div>
<div class="disclaimer">{discl}</div>
{body}
	<div class="footer">※ Dexterous Hand News Digest · roboticsdao.github.io</div>
{HISTORY_JS}</body></html>'''

def update_history(n):
    h = []
    if HISTORY_FILE.exists():
        try: h = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except: pass
    e = {"id": TODAY.strftime("%Y%m%d_%H%M"), "date": DATE_STR, "time": TIME_STR + " JST",
         "file": f"Dexterous_Hand_News_{TODAY.strftime('%Y%m%d')}.html", "count": n}
    h = [x for x in h if x["date"] != DATE_STR]
    h.insert(0, e)
    h = h[:90]
    HISTORY_FILE.write_text(json.dumps(h, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    print(f"🖐 Dexterous Hand News — {DATE_STR} ({WEEKDAY_JP})")
    print("=" * 50)
    print("\n📝 Generating digest...")
    digest = generate_digest()
    n = digest.count("- **") if digest else 0
    if n < MIN_DAILY_ITEMS:
        print(f"❌ Only {n} items")
        sys.exit(1)
    if not has_required_content(digest):
        print("❌ Missing a required region or minimum item count")
        sys.exit(1)
    if not validate_digest_quality(digest):
        print("❌ Refusing to publish repetitive or highly similar summaries")
        sys.exit(1)
    OUTPUT_FILE.write_text(digest, encoding="utf-8")
    html = md_to_html(digest)
    (OUTPUT_DIR / "latest.html").write_text(html, encoding="utf-8")
    dated = OUTPUT_DIR / f"Dexterous_Hand_News_{TODAY.strftime('%Y%m%d')}.html"
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
