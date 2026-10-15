import shutil
import hashlib
from pathlib import Path

root = Path(__file__).resolve().parents[1]
site = root / "_site"
if site.exists():
    shutil.rmtree(site)
site.mkdir()
for pattern in ("*.html", "*.json"):
    for path in root.glob(pattern):
        shutil.copy2(path, site / path.name)
for directory in ("hub", "dexterous-hand-news"):
    source = root / directory
    if not source.exists():
        continue
    for path in source.rglob("*"):
        if any(part in ("node_modules", ".git", "__pycache__") for part in path.parts):
            continue
        if path.is_file() and path.suffix in (".html", ".json", ".js", ".css", ".png", ".jpg", ".jpeg", ".webp", ".svg", ".ico", ".woff2"):
            target = site / path.relative_to(root)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
(site / ".nojekyll").touch()
portal = site / "hub" / "index.html"
if portal.exists():
    html = portal.read_text(encoding="utf-8")
    for asset in ("style.css", "app.js", "views.js", "graphs.js", "vendor/d3.min.js", "vendor/lucide.js"):
        version = hashlib.sha256((portal.parent / asset).read_bytes()).hexdigest()[:12]
        html = html.replace(f'"{asset}"', f'"{asset}?v={version}"')
    portal.write_text(html, encoding="utf-8")
print(f"Prepared {sum(1 for p in site.rglob('*') if p.is_file())} static files")
