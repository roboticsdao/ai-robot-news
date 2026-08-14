#!/usr/bin/env python3
import html
import os, subprocess, re, sys, time, json, unicodedata, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from difflib import SequenceMatcher
from datetime import datetime, timezone, timedelta
from pathlib import Path

from article_summaries import enrich_articles, summarize_articles, summary_quality_issues

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

PROMPT = f"""You are an AI robotics industry news editor. Today is {DATE_STR} ({WEEKDAY_EN}).

Search for the latest AI robotics news. Find 3-5 items for United States, China, and Japan. Also add a final "Humanoid Robotics" section with at least 5 non-duplicate global humanoid robotics items. Total 14-20 items.

RULES:
1. Prioritize last 24 hours. Expand only to the past 3 days if needed. NEVER use older items.
2. NEVER say sorry, unable to find, or anything similar. FORBIDDEN.
3. Each item must have: date, company name, a substantial summary, and source publication name.
4. Japan section must cover Japan's domestic AI/robotics industry only. Exclude China/Unitree stories merely reported in Japanese.
5. Humanoid Robotics section must cover embodied humanoid robot news globally. The first Humanoid Robotics item must be reserved for Japan's humanoid robotics industry and OmakaseRobotics/Omakase OS/D1 humanoid if any recent item is available.
6. Do NOT include any URLs in your response. I will add them separately.
7. Every summary must explain the specific event in that item's headline. Never reuse a sentence, closing paragraph, or generic "what to watch" list across different items.
8. The follow-up indicators must match the event type: regulation, financing, shipment data, product launch, field trial, technical research, hiring, or partnership require different analysis.

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

ROBOTICS_PROFILES = {
    "regulation": {
        "en": "The material change is the operating boundary: liability, permitted locations, human oversight, and incident reporting can determine whether deployment is legal before hardware performance is considered.",
        "zh": "它改变的是机器人的准入和责任边界，监管文本中的适用场所、人工监督、事故上报和责任主体，会先于硬件性能决定产品能否进入真实环境",
        "jp": "焦点は性能競争よりも運用条件です。利用場所、責任主体、人の監督、事故報告が明確になれば導入判断が進みますが、規制が曖昧なままでは顧客側の法務負担が残ります",
        "watch_zh": "正式规则的适用范围、企业合规方案、保险责任以及首批获准部署案例",
        "watch_en": "the final rule text, compliance plans, insurance allocation, and the first deployments approved under it",
        "watch_jp": "最終的な規則の範囲、企業の適合計画、保険・責任分担、承認後の最初の導入案件",
    },
    "market": {
        "en": "Shipment or share data measures commercial reach, but unit counts alone do not reveal selling price, customer concentration, utilization, or whether deliveries are recurring.",
        "zh": "出货量和市场份额能说明商业触达速度，却不能单独证明收入质量；平均售价、客户集中度、实际开机率和复购情况才决定这些数字是否可持续",
        "jp": "出荷台数やシェアは普及速度を示しますが、平均販売価格、顧客集中度、稼働率、再注文が分からなければ収益性までは判断できません",
        "watch_zh": "厂商口径是否一致、订单和交付是否匹配、海外占比以及售后服务成本",
        "watch_en": "consistent vendor definitions, order-to-delivery conversion, overseas mix, utilization, and support cost",
        "watch_jp": "集計基準の整合性、受注から納入への転換、海外比率、稼働率、保守コスト",
    },
    "finance": {
        "en": "The capital event changes runway and competitive pressure; its value depends on how much is allocated to engineering, factories, inventory, field support, and customer acquisition rather than valuation alone.",
        "zh": "资本事件首先改变企业的现金跑道和竞争压力，真正相关的是资金会投入研发、工厂、库存、现场支持还是获客，而不是只看融资额或估值数字",
        "jp": "資金調達は開発期間と競争環境を変えます。評価額だけでなく、研究開発、工場、在庫、現場支援、顧客獲得にどれだけ配分されるかが重要です",
        "watch_zh": "资金用途、现金消耗速度、下一阶段里程碑以及融资后新增的可验证客户",
        "watch_en": "use of proceeds, cash burn, the next technical milestone, and verifiable customers added after financing",
        "watch_jp": "資金使途、キャッシュ消費、次の技術マイルストーン、調達後に増えた検証可能な顧客",
    },
    "deployment": {
        "en": "A field deployment tests uptime, task completion, safety interventions, workflow integration, and labor savings under conditions that a staged demonstration cannot reproduce.",
        "zh": "现场部署验证的是连续运行时间、任务完成率、安全接管次数、客户流程接入和节省工时，这些指标比舞台演示更能说明机器人是否具备使用价值",
        "jp": "現場導入では、連続稼働時間、作業完了率、安全介入、既存業務との接続、省人効果が検証されます。展示だけでは確認できない運用性能が問われます",
        "watch_zh": "试点持续时长、人工接管频率、单任务成本、现场人员评价以及是否扩展到第二个地点",
        "watch_en": "pilot duration, intervention rate, cost per task, operator feedback, and expansion to a second site",
        "watch_jp": "実証期間、介入頻度、作業当たりコスト、現場評価、二つ目の拠点への展開",
    },
    "product": {
        "en": "A product announcement becomes commercially meaningful only when specifications, price, delivery date, developer access, and support obligations are concrete.",
        "zh": "产品发布只有在规格、售价、交货时间、开发接口和售后责任明确后才具备商业含义；展示视频本身无法证明量产一致性和长期可靠性",
        "jp": "製品発表は、仕様、価格、納期、開発者向け接続、保守条件が具体化して初めて商業的な意味を持ちます。映像だけでは量産品質を判断できません",
        "watch_zh": "正式规格与演示是否一致、首批交付时间、开发者工具、质保范围和客户订单",
        "watch_en": "whether final specifications match the demo, first delivery timing, developer tools, warranty terms, and customer orders",
        "watch_jp": "正式仕様とデモの一致、初回納入時期、開発ツール、保証範囲、顧客受注",
    },
    "research": {
        "en": "The technical claim matters through measurable improvement in data efficiency, perception, planning, control latency, or transfer from simulation to physical machines.",
        "zh": "技术进展应落到可测量指标上，例如数据效率、感知准确率、规划成功率、控制延迟，以及仿真能力能否迁移到实体机器，而不是只用“更智能”概括",
        "jp": "技術的価値は、データ効率、認識精度、計画成功率、制御遅延、シミュレーションから実機への移行で測る必要があります",
        "watch_zh": "公开基准、与现有方案的对照、真实机器人测试、复现实验和计算成本",
        "watch_en": "published benchmarks, comparisons with prior systems, tests on physical robots, reproducibility, and compute cost",
        "watch_jp": "公開ベンチマーク、既存方式との比較、実機試験、再現性、計算コスト",
    },
    "partnership": {
        "en": "The partnership is useful when each party contributes a defined asset such as hardware, software, facilities, distribution, or customer access and when ownership of deployment work is clear.",
        "zh": "合作价值取决于各方是否提供明确资源，例如硬件、软件、测试场地、渠道或客户入口，以及部署、数据和售后责任是否已经划分",
        "jp": "連携の価値は、各社がハードウェア、ソフトウェア、実証場所、販売網、顧客接点のどれを担うか、導入責任が明確かで決まります",
        "watch_zh": "联合项目时间表、双方交付物、数据权属、首个客户场景和合作是否具有排他性",
        "watch_en": "the joint timetable, each party's deliverables, data ownership, the first customer use case, and any exclusivity",
        "watch_jp": "共同計画の日程、各社の成果物、データ権利、最初の顧客用途、独占条件",
    },
    "people": {
        "en": "A leadership, advisory, hiring, or education move is an organizational signal; it matters only if the new capability changes product decisions, regulation access, recruiting, or execution speed.",
        "zh": "顾问任命、招聘或人才培养属于组织能力信号，关键不在头衔本身，而在新加入者能否改变产品决策、监管沟通、人才供给或项目执行速度",
        "jp": "顧問就任、採用、人材育成は組織能力のシグナルです。肩書ではなく、製品判断、規制対応、採用力、案件実行の速度が変わるかが重要です",
        "watch_zh": "其明确职责、参与项目、团队扩张、决策权限以及随后出现的产品或客户结果",
        "watch_en": "the person's defined remit, projects, team growth, decision authority, and subsequent product or customer outcomes",
        "watch_jp": "明確な担当範囲、参加案件、組織拡大、意思決定権、その後の製品・顧客成果",
    },
    "manufacturing": {
        "en": "Manufacturing progress affects delivery credibility and unit economics through yield, takt time, component availability, quality control, and service-parts planning.",
        "zh": "制造与交付进展会通过良率、节拍、关键零部件供应、质量控制和备件计划影响量产可信度与单机成本，不能只用产能目标判断",
        "jp": "生産進展は、歩留まり、タクトタイム、部品調達、品質管理、保守部品の計画を通じて納入能力と単価を左右します",
        "watch_zh": "实际周产量、良率、核心部件瓶颈、延期情况、单位成本和返修率",
        "watch_en": "actual weekly output, yield, component bottlenecks, delays, unit cost, and return or repair rates",
        "watch_jp": "実際の週産台数、歩留まり、部品制約、納期遅延、単価、修理率",
    },
    "consumer": {
        "en": "Consumer robots compete on daily usefulness, interaction quality, privacy, durability, and long-term service cost rather than industrial throughput.",
        "zh": "消费与陪伴机器人不以工业产能衡量，而要看日常使用频率、交互质量、隐私处理、耐用性和长期服务费用，体验新鲜感不等于留存",
        "jp": "家庭・伴走型ロボットでは、生産性より日常利用頻度、対話品質、プライバシー、耐久性、長期サービス費用が継続利用を決めます",
        "watch_zh": "用户留存、退货原因、订阅服务、隐私政策、软件更新周期和真实家庭反馈",
        "watch_en": "retention, return reasons, subscriptions, privacy policy, software-update cadence, and long-term household feedback",
        "watch_jp": "利用継続率、返品理由、課金サービス、プライバシー方針、更新周期、家庭での長期評価",
    },
    "general": {
        "en": "The report is an industry signal, but its significance depends on the concrete capability, customer, timetable, and operating metric named beyond the headline.",
        "zh": "这是一条产业信号，但其重要性仍取决于新闻能否给出明确能力、客户、时间表和运行指标；没有这些信息时，只能把它视为待验证线索",
        "jp": "産業シグナルではありますが、具体的な機能、顧客、日程、運用指標が示されなければ、現時点では検証待ちの情報です",
        "watch_zh": "后续公告中的量化指标、责任主体、落地时间、第三方验证和客户反馈",
        "watch_en": "quantified metrics, accountable owners, deployment timing, independent validation, and customer feedback",
        "watch_jp": "定量指標、責任主体、実施時期、第三者検証、顧客評価",
    },
}

def is_relevant_robotics_item(region, headline):
    lower = headline.lower()
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
    return all((parse_item_date(d) or TODAY.date()) >= CUTOFF_DATE for d in dates)

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
    required = {"🇺🇸": 3, "🇨🇳": 3, "🇯🇵": 3, "🤖": 5}
    return all(any(emoji in heading and count >= minimum for heading, count in counts.items()) for emoji, minimum in required.items())

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
            if not is_relevant_robotics_item(region, headline):
                continue
            seen.add(headline.lower())
            try:
                dt = datetime.strptime(published, "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=timezone.utc).astimezone(LOCAL_TZ)
                date = dt.strftime("%Y.%m.%d")
            except Exception:
                dt = TODAY
                date = DATE_STR
            if parse_item_date(date) < CUTOFF_DATE:
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

def short_event(headline, limit=90):
    clean = re.sub(r"\s+", " ", headline).strip()
    return clean if len(clean) <= limit else clean[:limit].rstrip() + "..."

def sentence_event(headline, limit=62):
    clean = re.sub(r"[.!?。！？\"“”]+", " ", headline)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean if len(clean) <= limit else clean[:limit].rstrip() + "…"

def english_summary(item):
    headline = item["headline"]
    source = item.get("source", "The source")
    topic = robotics_topic(headline)
    profile = ROBOTICS_PROFILES[topic]
    subject = ", ".join(extract_entities(headline))
    if subject == "the companies and institutions named in the headline":
        subject = source
    reference = sentence_event(headline, 40)
    short_reference = sentence_event(headline, 20)
    return (
        f'Summary: {source} reports "{reference}," an event affecting {subject}. '
        f'In {source}\'s "{short_reference}" case, {profile["en"][0].lower() + profile["en"][1:]} '
        f'For "{short_reference}," watch {profile["watch_en"]}.'
    )

def chinese_summary(item):
    headline = item["headline"]
    source = item.get("source", "新闻来源")
    entities = "、".join(extract_entities(headline))
    if entities == "the companies and institutions named in the headline":
        entities = source
    event = short_event(headline)
    reference = sentence_event(headline, 48)
    profile = ROBOTICS_PROFILES[robotics_topic(headline)]
    return (
        f"总结：{source}报道的具体事件是「{event}」。就「{reference}」而言，{profile['zh']}。"
        f"针对「{reference}」，后续应核实{profile['watch_zh']}。只有这些指标与该事件相互印证，"
        f"才能判断「{reference}」究竟改变了产品能力、商业节奏还是竞争位置；在没有进一步数据时，不把该标题之外的推测写成事实。"
    )

def japanese_summary(item):
    headline = item["headline"]
    source = item.get("source", "報道元")
    entities = "、".join(extract_entities(headline))
    if entities == "the companies and institutions named in the headline":
        entities = source
    profile = ROBOTICS_PROFILES[robotics_topic(headline)]
    reference = sentence_event(headline, 52)
    return (
        f"要約：{source}が報じた具体的な出来事は「{headline}」です。「{reference}」を評価する際、{profile['jp']}。"
        f"「{reference}」について次に確認すべきなのは、{profile['watch_jp']}です。"
        f"同件では見出しで確認できる事実と産業上の読み取りを分け、追加発表や数値が出るまでは「{reference}」から推測した商談、性能、量産計画を事実として扱いません。"
    )

def us_robotics_chinese_summary(item):
    return chinese_summary(item)

def japan_robotics_chinese_summary(item):
    return chinese_summary(item)

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
    source = item.get("source", "The source")
    topic = robotics_topic(headline)
    profile = ROBOTICS_PROFILES[topic]
    japan_priority = first and any(k in headline.lower() for k in ["omakase", "japan", "日本", "ヒューマノイド"])
    en = english_summary(item)
    if japan_priority:
        en += " This lead item is classified as the Japan/Omakase watch because the headline itself contains a Japan-linked humanoid signal."
    zh = chinese_summary(item)
    if japan_priority:
        zh += f" 本条进入日本/Omakase优先位的依据来自标题中的日本人形机器人线索；针对该事件只追踪{profile['watch_zh']}，不套用其他公司的量产或试点判断。"
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
            f"  English: {english_summary(item)}",
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
        "> ⚠️ 本日报收录近3天 AI 机器人新闻；摘要仅压缩媒体原文中明确出现的事实，不添加商业判断或后续预测。",
        "",
        "---",
    ]

    grouped_items = []
    global_headlines = []
    for region in REGIONS:
        print(f"   RSS/body fetch: {region['emoji']} {region['label']}")
        target = region.get("min_items", 5)
        candidate_limit = target + 8
        try:
            candidates = fetch_humanoid_items(region, candidate_limit, exclude_headlines=global_headlines) if region["label"] == "Humanoid Robotics" else fetch_rss_items(region, candidate_limit, exclude_headlines=global_headlines)
            for item in candidates:
                item["summary_language"] = "Japanese" if region["emoji"] == "🇯🇵" else "Chinese" if region["emoji"] == "🇨🇳" else "English"
                item["region_label"] = region["label"]
            items = enrich_articles(candidates)[:target]
        except Exception as e:
            print(f"   Article fetch error for {region['label']}: {e}")
            items = []
        global_headlines.extend(item["headline"] for item in items)
        grouped_items.append((region, items))

    flat_items = [item for _, items in grouped_items for item in items]
    summarized = summarize_articles(flat_items, GEMINI_API_KEY)
    issues = summary_quality_issues(summarized)
    if issues:
        raise RuntimeError("; ".join(issues[:5]))
    summarized_by_region = {}
    for item in summarized:
        summarized_by_region.setdefault(item["region_label"], []).append(item)

    total = 0
    for region, _ in grouped_items:
        items = summarized_by_region.get(region["label"], [])
        parts.append(f"\n## {region['emoji']} {region['label']}\n")
        if not items:
            parts.append(f"- **[{DATE_STR}] No readable source — 暂无可读取全文的新闻**\n  中文：本地区近期文章正文均无法可靠读取，因此未生成推测性摘要。\n  📰 Google News")
            continue
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
	<title>AI Robot News | {DATE_STR}</title><style>{CSS}</style>{THEME_JS}</head><body>
	<div class="top-bar"><div class="history-wrap"><button class="history-btn" id="historyBtn"><svg viewBox="0 0 16 16"><path d="M8 1a7 7 0 1 0 0 14A7 7 0 0 0 8 1zm0 12.5A5.5 5.5 0 1 1 8 2.5a5.5 5.5 0 0 1 0 11zM8.5 4h-1v4.5l3.5 2 .5-.87-3-1.75V4z"/></svg>历史记录</button><div class="history-panel" id="historyPanel"><h3>📅 刷新记录</h3><div id="historyList"></div></div></div><div class="top-actions"><div class="updated-at">更新于 {TIME_STR} JST</div><button class="theme-btn" id="themeBtn" type="button"><span id="themeIcon" aria-hidden="true">◐</span></button></div></div>
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
