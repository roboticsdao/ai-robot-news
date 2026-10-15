# AI Robot News

## Published Pages

- [Integrated intelligence hub](https://roboticsdao.github.io/ai-robot-news/hub/)
- [AI Robot daily](https://roboticsdao.github.io/ai-robot-news/latest.html)
- [Dexterous Hand daily](https://roboticsdao.github.io/ai-robot-news/dexterous-hand-news/latest.html)
- [Stock Market daily](https://roboticsdao.github.io/stock-market-daily/latest.html)

The existing editions remain available. The hub adds a company/funding/supply-chain
index and combines the three structured feeds without calling an AI API in the browser.
Visiting a page does not consume Gemini tokens.

## Generation And Deployment

GitHub Actions runs in GitHub's cloud; a Mac does not need to stay on.
AI Robot runs at approximately 08:10 and 20:10 JST. Dexterous Hand runs at 08:00 JST.
Stock Market uses the schedule in its own repository (08:00, 21:00, 22:15, 23:00 JST).
GitHub scheduling may be delayed. The stock refreshes bracket US pre-market/open
across daylight-saving changes; they are not an exchange-synchronized quote stream.

Each generator reads original article bodies, produces source-language and Chinese
summaries, validates source dates and duplicates, and commits HTML plus `feed.json`
and `status.json`. Summaries describe the article rather than giving investment or
commercialization advice. API failure falls back to factual source-language extracts,
not fabricated Chinese summaries.

`tools/build_portal.py` refreshes the attributed public fact index and integrates
the current feeds and recent archives. Reference or stock-feed outages retain their
dated cached snapshots. Old template-based paragraphs are not republished as full-text
summaries. Original publisher links are retained.

Bot pushes explicitly dispatch `pages.yml`: pushes made with `GITHUB_TOKEN` do not
trigger another workflow's `push` event. Pages exports only static assets; Jekyll is
not used. Transient Pages deployment failures get one bounded retry. Do not replace
this with `continue-on-error` on the whole job, or disable failure notifications.

An individual section below its editorial target is marked `partial`, preserving
other verified fresh sections. Zero real articles, invalid dates, and repeated or
unreadable content still block publication and retain the previous edition.
Quote snapshots never satisfy the article minimum.

## Local Checks

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s . -v
python -m unittest discover -s dexterous-hand-news -v
python tools/build_portal.py --offline --stock-dir ../stock-market-daily
python tools/prepare_site.py
python -m http.server 8874
```

Open `http://localhost:8874/hub/`. To refresh the reference index, omit `--offline`.
Committed `hub/vendor` files allow GitHub Pages deployment without npm or a bundler.
To update browser libraries, use `npm ci` inside `hub`, then run the portal builder.
Never put API keys, access tokens or `.env` files in the static directory.

For a failed run, inspect the failed step and original exception in Actions, then
dispatch the corresponding generator. Check `/hub/#status` and the public feed dates
after Pages completes; a successful HTML download alone is not content verification.

See [reference-analysis.md](reference-analysis.md) for the feature inventory and
[design-qa.md](design-qa.md) for browser verification evidence.
