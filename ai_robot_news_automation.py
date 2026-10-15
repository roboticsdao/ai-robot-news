#!/usr/bin/env python3
import html
import os, subprocess, re, sys, time, json, unicodedata, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from difflib import SequenceMatcher
from datetime import datetime, timezone, timedelta
from pathlib import Path

from article_summaries import deduplicate_summaries, enrich_articles, fetch_rss_bytes, remove_repeated_summary_sentences, summarize_articles, summary_quality_issues
from edition_health import publisher_candidates, write_feed

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
            "日本 ロボット 企業",
            "ロボット 実証 日本",
            "ロボット 導入 国内",
            "フィジカルAI 日本 企業",
            "人手不足 ロボット 日本",
            "日本 ロボット AI",
            "国内 ロボット AI",
            "日本 ヒューマノイド ロボット",
            "日本 フィジカルAI ロボット",
            "ソニー アイボ ロボット",
            "AGRIST 収穫ロボット AI",
            "ファナック ロボット AI",
            "安川電機 ロボット AI",
            "川崎重工 ロボット AI 日本",
            "トヨタ ロボット AI 日本",
            "ホンダ ロボット AI 日本",
            "Telexistence ロボット 日本",
            "オムロン 産業用ロボット AI",
            "デンソー ロボット AI 日本",
            "Mujin ロボット 日本",
        ],
        "hl": "ja",
        "gl": "JP",
        "ceid": "JP:ja",
        "exclude_terms": ["中国", "China", "中国製", "中国経済", "人民網", "Unitree", "ユニツリー", "宇樹", "宇树", "매일경제", "디지털투데이", "Mshale", "Orbbec", "SwitchBot"],
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
    if any(term in lower for term in ("harassment", "alleged assault", "police seize", "robot attends parade", "parade of")):
        return False
    robotics_terms = ["robot", "robotic", "humanoid", "physical ai", "embodied ai", "ロボット", "ヒューマノイド", "机器人", "具身智能"]
    humanoid_terms = ["humanoid", "bipedal", "optimus", "figure ai", "apptronik", "agility robotics", "atlas", "unitree", "ubtech", "agibot", "fourier", "omakase", "ヒューマノイド", "人形机器人", "人型机器人"]
    if region["label"] == "Humanoid Robotics":
        return any(term in lower for term in humanoid_terms)
    if region["emoji"] == "🇺🇸":
        us_markers = ["u.s.", " us ", "america", "tesla", "figure", "boston dynamics", "nvidia", "amazon", "apptronik", "agility"]
        return any(term in lower for term in robotics_terms) and any(term in f" {lower} " for term in us_markers)
    if region["emoji"] == "🇯🇵" and any(term in lower for term in ["韓国", "korea", "한국", "中国", "china", "unitree", "ユニツリー"]):
        return False
    if region["emoji"] == "🇯🇵":
        japan_markers = [
            "日本", "国内", "安川", "ファナック", "川崎重工", "トヨタ", "ホンダ", "ソニー", "aibo",
            "agr ist", "agrist", "telexistence", "オムロン", "デンソー", "mujin", "日立", "三菱電機",
            "パナソニック", "産総研", "東京大学", "大阪大学", "早稲田", "慶應", "自治体",
            "ロボットビジネス支援機構", "静岡市", "清水区役所", "岡山大学", "豊田通商", "triorb",
            "タカラスタンダード", "sert", "zeals", "未来館", "jst", "中日", "北海道",
        ]
        return any(term in lower for term in robotics_terms) and any(term in lower for term in japan_markers)
    return any(term in lower for term in robotics_terms)

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
    # Per-section targets are availability goals, not evidence of a system crash.
    return sum(counts.values()) >= 3 and all(
        any(emoji in heading for heading in counts) for emoji in ("🇺🇸", "🇨🇳", "🇯🇵", "🤖")
    )

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
    humanoid = any(term in headline.lower() for term in ["humanoid", "ヒューマノイド", "人形机器人", "人型机器人"])
    for other in other_headlines:
        other_canonical = canonical_headline(other)
        if canonical == other_canonical:
            return True
        if min(len(canonical), len(other_canonical)) >= 24 and SequenceMatcher(None, canonical, other_canonical).ratio() >= 0.78:
            return True
        other_tokens = headline_tokens(other)
        shared_tokens = tokens & other_tokens
        token_union = tokens | other_tokens
        if len(shared_tokens) >= 4 and token_union and len(shared_tokens) / len(token_union) >= 0.35:
            return True
        other_entities = {name.lower() for name in extract_entities(other) if not name.startswith("the companies")}
        other_humanoid = any(term in other.lower() for term in ["humanoid", "ヒューマノイド", "人形机器人", "人型机器人"])
        if humanoid and other_humanoid and len(entities & other_entities) >= 2:
            return True
    return False

def fetch_rss_items(region, limit=5, exclude_headlines=None):
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
            "q": f"{scoped_query} when:3d",
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
            if parse_item_date(date) < CUTOFF_DATE or dt > TODAY:
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
        topic_limit = 1 if region["label"] == "Humanoid Robotics" and topic == "market" else 2
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
        "Boston Dynamics", "Hyundai", "Tesla", "Figure", "NVIDIA", "LG", "Amazon", "Microsoft", "Google",
        "Unitree", "宇树", "优必选", "UBTech", "小鹏", "华为", "阿里巴巴", "腾讯", "百度",
        "AGRIST", "Sony", "ソニー", "aibo", "ファナック", "安川電機", "Telexistence", "SoftBank", "GMO", "Toyota", "Honda",
    ]
    found = [name for name in names if name.lower() in headline.lower()]
    return found[:4] or ["the companies and institutions named in the headline"]











def generate_digest_from_rss():
    parts = [
        f"# 🤖 AI Robot News | {DATE_STR}（{WEEKDAY_JP}曜日 / {WEEKDAY_EN}）",
        "",
        "> ⚠️ 本日报收录近3天 AI 机器人新闻；摘要仅压缩媒体原文中明确出现的事实，不添加商业判断或后续预测。",
        "",
        "---",
    ]

    grouped_items = []
    global_headlines = []
    for region in sorted(REGIONS, key=lambda r: r["label"] != "Humanoid Robotics"):
        print(f"   RSS/body fetch: {region['emoji']} {region['label']}")
        target = region.get("min_items", 5)
        candidate_limit = target + 8
        try:
            candidates = fetch_humanoid_items(region, candidate_limit, exclude_headlines=global_headlines) if region["label"] == "Humanoid Robotics" else fetch_rss_items(region, candidate_limit, exclude_headlines=global_headlines)
            for item in candidates:
                item["summary_language"] = "Japanese" if region["emoji"] == "🇯🇵" else "Chinese" if region["emoji"] == "🇨🇳" else "English"
                item["region_label"] = region["label"]
            items = enrich_articles(candidates)[:target + 3]
            if len(items) < target:
                feeds = ["https://rss.itmedia.co.jp/rss/2.0/monoist.xml"] if region["emoji"] == "🇯🇵" else ["https://www.ithome.com/rss/"] if region["emoji"] == "🇨🇳" else ["https://www.therobotreport.com/feed/", "https://roboticsandautomationnews.com/feed/"]
                fallback = publisher_candidates(
                    feeds, TODAY - timedelta(days=3), TODAY,
                    lambda title: is_relevant_robotics_item(region, title), fetch_rss_bytes,
                )
                fallback = [i for i in fallback if not duplicate_story(i["headline"], global_headlines + [j["headline"] for j in items])]
                for item in fallback:
                    item["summary_language"] = "Japanese" if region["emoji"] == "🇯🇵" else "Chinese" if region["emoji"] == "🇨🇳" else "English"
                    item["region_label"] = region["label"]
                items.extend(enrich_articles(fallback[:16]))
            print(f"   Readable full-text items: {len(items)}")
        except Exception as e:
            print(f"   Article fetch error for {region['label']}: {e}")
            items = []
        global_headlines.extend(item["headline"] for item in items)
        grouped_items.append((region, items))

    flat_items = [item for _, items in grouped_items for item in items]
    summarized = summarize_articles(flat_items, GEMINI_API_KEY)
    summarized, removed = deduplicate_summaries(summarized)
    summarized, sentence_repairs = remove_repeated_summary_sentences(summarized)
    if removed or sentence_repairs:
        print(f"   Removed {len(removed)} duplicate articles; repaired {len(sentence_repairs)} repeated sentences")
    issues = summary_quality_issues(summarized)
    if issues:
        raise RuntimeError("; ".join(issues[:5]))
    summarized_by_region = {}
    for item in summarized:
        summarized_by_region.setdefault(item["region_label"], []).append(item)

    total = 0
    published_items = []
    for region in REGIONS:
        items = summarized_by_region.get(region["label"], [])[:region.get("min_items", 5)]
        parts.append(f"\n## {region['emoji']} {region['label']}\n")
        if not items:
            parts.append("> 当前时段暂无可核实的最新全文，其他板块照常更新；未用旧稿或标题推测补数。")
            continue
        if len(items) < region.get("min_items", 5):
            parts.append(f"> 本轮核实 {len(items)} 条新闻，未达到目标数量；不重复收录或编造补数。")
        published_items.extend(items)
        for item in items:
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

    digest = "\n\n".join(parts)
    if not has_required_content(digest) or not validate_digest_quality(digest):
        raise RuntimeError("No publishable verified robot edition; preserving the previous edition")
    write_feed(OUTPUT_DIR, published_items, "robot", TODAY, {r["label"]: r.get("min_items", 5) for r in REGIONS})
    parts.append(f"\n---\n※AI Robot News Digest | {DATE_STR} | full-text items: {total}")
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
    notices = {}
    for line in md.split("\n"):
        s = line.strip()
        if s.startswith("> "):
            if cur:
                notices[cur[1]] = s[2:].strip()
            else:
                discl = s[2:].strip()
        elif s.startswith("## "):
            if cur:
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
    if cur:
        regions.append((cur, items))

    parts = []
    for (flag, label), itms in regions:
        parts.append(f'<div class="region"><div class="region-head">{flag} {label}</div>')
        if label in notices:
            parts.append(f'<p class="item-en">{html.escape(notices[label])}</p>')
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
	<title>AI Robot News | {DATE_STR}</title><style>{CSS}</style>{THEME_JS}</head><body>
	<div class="top-bar"><div class="history-wrap"><button class="history-btn" id="historyBtn"><svg viewBox="0 0 16 16"><path d="M8 1a7 7 0 1 0 0 14A7 7 0 0 0 8 1zm0 12.5A5.5 5.5 0 1 1 8 2.5a5.5 5.5 0 0 1 0 11zM8.5 4h-1v4.5l3.5 2 .5-.87-3-1.75V4z"/></svg>历史记录</button><div class="history-panel" id="historyPanel"><h3>📅 刷新记录</h3><div id="historyList"></div></div></div><div class="top-actions"><a href="hub/" style="font-size:12px;color:var(--link);white-space:nowrap">产业图谱</a><div class="updated-at">更新于 {TIME_STR} JST</div><button class="theme-btn" id="themeBtn" type="button"><span id="themeIcon" aria-hidden="true">◐</span></button></div></div>
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
    if not has_required_content(digest):
        print("❌ Missing a required region or minimum item count")
        sys.exit(1)
    if not validate_digest_quality(digest):
        print("❌ Refusing to publish repetitive or highly similar summaries")
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
