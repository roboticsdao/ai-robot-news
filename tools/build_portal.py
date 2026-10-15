"""Build a static, attributed fact index. Never execute upstream JavaScript."""
import argparse
import hashlib
import json
import re
import shutil
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HUB = ROOT / "hub"
DATA = HUB / "data"
REFERENCE = "https://xiaotong.me/RobotOverflow/"
FIELDS = ("id", "name", "seg", "cc", "city", "stage", "home", "domain", "logo", "parent", "val", "valKind", "raised", "heads", "founded", "founders")


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "RoboticsDAO-News/1.0", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(request, timeout=25) as response:
        return response.read()


def parse_reference(raw):
    raw = re.sub(r"\A\s*/\*.*?\*/\s*", "", raw, count=1, flags=re.S)
    match = re.fullmatch(r"\s*window\.DATA\s*=\s*(\{.*\})\s*;?\s*", raw, re.S)
    if not match:
        raise ValueError("Reference must be a JSON assignment, not executable JavaScript")
    data = json.loads(match.group(1))
    if not isinstance(data.get("companies"), list) or not isinstance(data.get("news"), list):
        raise ValueError("Reference schema changed")
    return data


def canonical_url(url):
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return ""
    query = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query) if not k.startswith("utm_") and k not in ("fbclid", "gclid")]
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc.lower(), parts.path.rstrip("/"), urllib.parse.urlencode(query), ""))


def classify(title, kind="robot"):
    if kind == "hand":
        return "hands"
    if kind == "market":
        return "markets"
    value = title.lower()
    groups = [
        ("hands", ("dexter", "robot hand", "robotic hand", "gripper", "灵巧手", "夹爪", "ロボットハンド")),
        ("components", ("sensor", "actuator", "lidar", "芯片", "传感", "执行器", "减速器", "supply chain", "供应链")),
        ("brains", ("model", "dataset", "foundation", "大模型", "模型", "数据", "训练", "世界模型", "open source", "开源")),
        ("business", ("fund", "invest", "merger", "acquir", "融资", "收购", "投资", "ipo", "上市", "政策")),
    ]
    return next((topic for topic, terms in groups if any(term in value for term in terms)), "robots")


def markdown_articles(text, kind):
    section = "Global"
    articles = []
    current = None
    for line in text.splitlines():
        clean = line.strip()
        if clean.startswith("## "):
            section = clean[3:]
        match = re.match(r"^- \*\*\[([\d.\-/]+)\] (.*?)\*\*", clean)
        if match:
            current = None
            if "行情快照 / Quote" in match[2] or "No readable source" in match[2]:
                continue
            source, _, headline = match[2].partition(" — ")
            current = {"date": match[1], "headline": headline or source, "source": source,
                       "section": section, "summary": "", "summary_zh": "", "url": "", "kind": kind}
            articles.append(current)
        elif current:
            if re.match(r"^(English|En|日本語)\s*[：:]", clean, re.I):
                current["summary"] = re.split(r"[：:]", clean, maxsplit=1)[1].strip()
                current["language"] = "Japanese" if clean.startswith("日本語") else "English"
            elif clean.startswith("中文"):
                current["summary_zh"] = re.sub(r"^中文\s*[：:]\s*(总结[：:]\s*)?", "", clean)
            elif clean.startswith("📰"):
                link = re.search(r"\]\((https?://[^)]+)\)", clean)
                if link:
                    current["url"] = link[1]
    return [a for a in articles if a["url"] and (a["summary"] or a["summary_zh"])]


def own_articles(stock_dir=None):
    result, states = [], {}
    for directory, kind, pattern in [(ROOT, "robot", "AI_Robot_News_*.md"), (ROOT / "dexterous-hand-news", "hand", "Dexterous_Hand_News_*.md")]:
        for path in sorted(directory.glob(pattern))[-90:]:
            result.extend(markdown_articles(path.read_text(encoding="utf-8"), kind))
        path = directory / "feed.json"
        if path.exists():
            feed = json.loads(path.read_text(encoding="utf-8"))
            result.extend(dict(a, kind=kind) for a in feed["articles"])
            states[kind] = feed.get("status", {})
    stock_cache = DATA / "market-cache.json"
    try:
        if stock_dir and (stock_dir / "feed.json").exists():
            stock = json.loads((stock_dir / "feed.json").read_text(encoding="utf-8"))
        else:
            stock = json.loads(fetch("https://roboticsdao.github.io/stock-market-daily/feed.json"))
        if not isinstance(stock.get("articles"), list):
            raise ValueError("invalid stock feed")
        stock_cache.write_text(json.dumps(stock, ensure_ascii=False), encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"Stock snapshot unavailable: {exc}; retaining cached snapshot")
        stock = json.loads(stock_cache.read_text(encoding="utf-8")) if stock_cache.exists() else {}
        if stock_dir:
            for path in sorted(stock_dir.glob("Stock_Market_Daily_*.md"))[-90:]:
                result.extend(markdown_articles(path.read_text(encoding="utf-8"), "market"))
    result.extend(dict(a, kind="market") for a in stock.get("articles", []))
    states["market"] = stock.get("status", {})
    return result, states


def clean_reference(raw):
    data = {key: raw.get(key, {}) for key in ("asOf", "nextRun", "segments", "layers", "layerGroups", "valHist", "betHist", "rounds", "months")}
    data["companies"] = [{k: c[k] for k in FIELDS if k in c} for c in raw["companies"]]
    for company in data["companies"]:
        if isinstance(company.get("name"), str):
            company["name"] = {"en": company["name"], "zh": company["name"]}
    data["kpis"] = {key: {k: profile["kpi"][k] for k in ("en", "zh", "value", "note", "src") if k in profile["kpi"]}
                    for key, profile in raw.get("profiles", {}).items() if isinstance(profile.get("kpi"), dict)}
    data["edges"] = [{k: e[k] for k in ("a", "b", "type", "from", "to", "conf", "src", "tag") if k in e} for e in raw.get("edges", [])]
    data["debates"] = [{k: d[k] for k in ("id", "q", "left", "right", "pos") if k in d} for d in raw.get("debates", [])]
    data["betEvidence"] = {company: {axis: [{k: row[k] for k in ("d", "p", "c", "s") if k in row} for row in rows]
                                      for axis, rows in axes.items()} for company, axes in raw.get("betWhy", {}).items()}
    data["stack"] = {}
    for company, layers in raw.get("stack", {}).items():
        data["stack"][company] = {
            layer: [[row[0], row[1], {k: row[2][k] for k in ("s", "c") if k in row[2]} if len(row) > 2 and isinstance(row[2], dict) else {}] for row in rows]
            for layer, rows in layers.items()
        }
    data["roadmap"] = [{"id": r["id"], "items": [{k: m[k] for k in ("d", "label", "s", "src", "src2", "target") if k in m} for m in r["items"]]} for r in raw.get("roadmap", [])]
    data["news"] = [{k: n[k] for k in ("d", "tags", "title", "cos", "src", "url", "conf", "imp") if k in n} for n in raw["news"]]
    return data


def company_matches(headline, companies):
    text = headline.lower()
    aliases = {"nvidia": ["英伟达", "エヌビディア"], "tesla": ["特斯拉", "テスラ"], "omakase": ["omakase"], "microsoft": ["微软"], "amazon": ["亚马逊"], "gdm": ["deepmind", "谷歌"], "bd": ["boston dynamics", "波士顿动力"]}
    found = []
    for company in companies:
        names = list(company.get("name", {}).values()) + aliases.get(company["id"], [])
        if company["id"] == "humanoid":
            names = ["HMND", "Humanoid Robotics", "Humanoid Limited", "Humanoid's", "Humanoid CEO"]
        elif company["id"] == "sunday":
            names = ["Sunday Robotics", "Sunday's robot", "Sunday机器人", "Sunday 机器人"]
        if any(name_matches(name, text) for name in names):
            found.append(company["id"])
    return found


def name_matches(name, text):
    name = name.lower()
    if re.search(r"[\u3040-\u9fff]", name):
        return len(name) >= 2 and name in text
    if len(name) < 3 and name not in ("1x",):
        return False
    return re.search(r"(?<![a-z0-9])" + re.escape(name) + r"(?![a-z0-9])", text.lower()) is not None


def merge_news(reference, articles, companies):
    merged = {}
    for item in reference:
        url = canonical_url(item.get("url", ""))
        if not url:
            continue
        value = dict(item, origin="reference", kind="robot", topic=classify(item.get("title", {}).get("en", "") + item.get("title", {}).get("zh", "")))
        value["id"] = hashlib.sha256(url.encode()).hexdigest()[:16]
        merged[url] = value
    for article in articles:
        url = canonical_url(article.get("url", ""))
        date = article.get("date", "").replace(".", "-").replace("/", "-")
        if not url or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            continue
        current = merged.get(url, {})
        title = current.get("title") or {"en": article["headline"], "zh": article["headline"]}
        legacy_template = any(term in (article.get("summary", "") + article.get("summary_zh", "")).lower()
                              for term in ("后续要看", "后续应关注", "这条消息涉及", "the practical read-through", "is reporting a specific"))
        current.update({"id": hashlib.sha256(url.encode()).hexdigest()[:16], "url": article["url"], "d": date,
                        "title": title, "src": article.get("source", ""), "origin": "digest",
                        "summary": article.get("summary", ""), "summary_zh": article.get("summary_zh", ""),
                        "language": article.get("language", "English"), "section": article.get("section", ""),
                        "published_at": article.get("published_at"), "kind": article["kind"],
                        "topic": classify(article["headline"], article["kind"]),
                        "cos": current.get("cos") or company_matches(article["headline"], companies),
                        "tags": current.get("tags", []), "conf": "body-read"})
        if legacy_template:
            current.update(summary="", summary_zh="", origin="archive", conf="indexed")
        merged[url] = current
    return sorted(merged.values(), key=lambda row: (row["d"], row.get("published_at") or ""), reverse=True)[:6000]


def download_logos(companies):
    def one(company):
        name = company.get("logo", "")
        if not re.fullmatch(r"assets/logos/[\w.-]+\.(png|jpg|webp|svg)", name):
            return
        path = HUB / name
        if path.exists():
            return
        try:
            content = fetch(REFERENCE + name)
            if len(content) < 100:
                return
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        except OSError:
            pass
    with ThreadPoolExecutor(max_workers=6) as executor:
        list(executor.map(one, companies))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stock-dir", type=Path)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)
    cache = DATA / "reference.json"
    try:
        if args.offline:
            raise OSError("offline")
        reference = clean_reference(parse_reference(fetch(REFERENCE + "assets/data.js").decode()))
        cache.write_text(json.dumps(reference, ensure_ascii=False), encoding="utf-8")
    except (OSError, ValueError) as exc:
        if not cache.exists():
            raise RuntimeError("No valid reference snapshot available") from exc
        reference = json.loads(cache.read_text(encoding="utf-8"))
        print(f"Reference update unavailable: {exc}; using snapshot dated {reference['asOf']}")
    companies = reference["companies"]
    if not any(c["id"] == "omakase" for c in companies):
        companies.append({"id": "omakase", "name": {"en": "Omakase Robotics", "zh": "Omakase Robotics"}, "seg": "maker", "cc": "JP", "stage": "Unknown"})
    articles, states = own_articles(args.stock_dir)
    news = merge_news(reference.pop("news"), articles, companies)
    catalog = dict(reference, news=news, feed_status=states,
                   built_at=datetime.now(timezone.utc).isoformat(), reference_url=REFERENCE)
    (DATA / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False), encoding="utf-8")
    if not args.offline:
        download_logos(companies)
    for source, target in [("d3/dist/d3.min.js", "d3.min.js"), ("lucide/dist/umd/lucide.js", "lucide.js")]:
        path = HUB / "node_modules" / source
        if path.exists():
            (HUB / "vendor").mkdir(exist_ok=True)
            shutil.copy2(path, HUB / "vendor" / target)
    print(f"Portal: {len(companies)} companies, {len(news)} stories, {len(catalog['edges'])} relations; reference as of {catalog['asOf']}")


if __name__ == "__main__":
    main()
