# Design And Functional QA

Date: 2026-10-15. Target: RobotOverflow's functional structure, adapted to RoboticsDAO
and the user's three existing daily feeds. This is not a claim of pixel-identical branding.

## Evidence And Normalization

- Source: https://xiaotong.me/RobotOverflow/
- Local implementation: http://127.0.0.1:8874/ai-robot-news/hub/
- Source screenshots: workspace `output/robotoverflow-reference/`.
- Implementation screenshots: workspace `output/playwright/final-*.png`.
- Desktop: 1440 x 960 CSS/pixels, device scale factor 1 for both sources.
- Mobile: 390 x 844 CSS/pixels, device scale factor 1 for both sources.
- Additional layout checks: 768 x 960 and 2560 x 960.
- Light theme, Chinese interface, corresponding routes. News content dates differ:
  the reference snapshot includes Oct 14 events; the implementation also includes
  Oct 15 original daily articles. English/Japanese source headlines are not relabeled
  as Chinese translations.
- Full-view paired inputs inspected: `compare-news-desktop.png`,
  `compare-news-mobile.png`, `compare-network-desktop.png`, `compare-company-desktop.png`.
- Focused typography/spacing input: `compare-news-focused.png` (720 x 420 crops side by side).
- Comparisons combine both images in the same input, not separate remembered views.

## Findings And Iterations

1. [P1, fixed] Company-name substring matching linked inflation news to ATI and
   generic humanoid stories to the company Humanoid. Added Latin word boundaries,
   strict aliases for ambiguous company names and regression tests. Rebuilt catalog;
   final news captures no longer show these false associations.
2. [P1, fixed] Nested supplier-group data made Anatomy throw instead of rendering.
   Normalize nested suppliers; final Anatomy shows all 14 layers and loaded bitmap.
3. [P1, fixed] Clicking the settings icon could close its own menu after icon repaint.
   Use the composed event path. Verified menu remains open after theme and language changes.
4. [P2, fixed] Modal back navigation relied on browser history length, which stops
   increasing after Chromium's history cap. Replaced with a private modal trail;
   Figure -> NVIDIA -> back -> forward and subsequent evidence navigation pass.
5. [P2, fixed] Initial network targets crowded same-category labels. Distribute
   chain-layout targets by segment and row. Final paired network capture separates
   suppliers, makers, brains, investors and deployers; zoom and alternate clustering work.
6. [P2, fixed] Several company-table headers appeared sortable but compared valuation
   regardless of selected key. Implemented string/numeric/news/stack comparisons;
   People descending now puts Amazon's recorded headcount first.
7. [P2, fixed] Historical template paragraphs could appear as read source summaries.
   Mark those entries as archive-only indexes with original links and no invented body.

Final comparison found no remaining actionable P0/P1/P2 issue within this adapted scope.

## Required Fidelity Surfaces

- Fonts/typography: restrained system sans, compact operational headings, 12-14 px
  list text, clear meta hierarchy, zero letter spacing. Native long headlines wrap
  without single-character columns. No oversized marketing typography.
- Spacing/layout: full-width unframed sections, compact tables and top navigation,
  right context rail on desktop, bottom navigation on mobile. Search/filter and health
  rows intentionally add vertical space versus the reference. Tables/timelines scroll
  within their own surfaces, not the document.
- Colors/tokens: white/light gray, blue action color, multicolor category/status encoding;
  dark charcoal mode and system preference verified. No decorative gradient/orb theme.
- Image/asset quality: locally stored real company logos; original generated generic
  robot bitmap rather than copied reference branding. Correct aspect ratios and sharpness.
  No source-hotlinked images or imitation CSS/SVG illustrations. Final browser run
  reports zero failed asset requests; nonblank screenshot pixel standard deviations
  exceed 27 in all RGB channels for tested news/network/detail comparison captures.
- Copy/content: RobotOverflow attribution and original evidence retained. Market cap,
  valuation, raised funds, production KPI and sales remain separate. Unknown facts stay
  unknown. Classified positions are not presented as company statements. Partial and
  overdue feeds are visible; data build time is not treated as article publication time.

## Interaction Verification

Passed in the independent Playwright browser authorized by the user:

- All 13 routes at 1440/390/768/2560 widths; no document horizontal overflow.
- Search and no-results state; 22 NVIDIA matches during the tested snapshot.
- Story bookmark, saved-only filtering and persistence after reload.
- Company all/none, search (Figure returns one company), category selection and shared state.
- Light/dark/system settings, Chinese/English interface, persistent preferences.
- Figure company detail, 65 evolution events, KPI evidence, nested NVIDIA navigation,
  internal back/forward, route-evidence popup and context pin.
- Sort by people; financing and event charts render real records.
- Network supplier filter changes 172 nodes / 723 relations to 167 / 422;
  alternate layouts, raised-capital sizing, zoom, month slider and 2024-11 -> 2024-12 playback.
- Multi-axis screener (52 matching companies for the tested pick), reset and axis selection.
- Mobile bottom-menu navigation to Dexterous Hand.
- Final route/interaction run: zero JavaScript errors and zero failed resource requests.
- Python unit suites: AI root 31, Dexterous Hand 29, Stock Market 29, all passed.

Final content verification additionally found a refused/malformed model batch had
discarded five Chinese summaries while leaving valid source extracts. Batch parse
failures now retry articles individually; one refused article cannot discard other
translations. Missing translations are explicit partial-health data. Off-topic,
duplicated harassment/parade coverage is excluded from the robotics industry feed.
Unused title-based template generators were removed from all three code paths.

## Final Production Verification

The final generators completed successfully: AI Robot run `38664462803`, Dexterous
Hand run `38664431644`, and Stock Market run `38664465241`. Published feeds contain
20 / 8 / 23 source articles respectively, each with a nonempty Chinese summary;
`translations_missing` is zero for all three. Stock has 8 US, 7 Japan and 8 macro
articles in addition to separate quote supplements. AI's 5 humanoid entries cover
Japan/GMO, automotive logistics, Unitree locomotion, commercial laundry and Agility's
SEC milestone, not repeated coverage of a harassment incident.

The deployed hub and old pages were opened in the independent browser. All 13 hub
routes passed production desktop/mobile checks without document overflow, JavaScript
errors or failed resource requests. Original pages also passed 390/2560 width checks,
theme switching, original-link presence and history loading.

The static exporter adds content hashes to CSS/JS URLs so a new deployment does not
reuse an old cached application bundle. A mocked missing-translation state visibly
showed the partial-health banner and missing count, then the interception was removed.

Earlier local HTTP backlog resets were resolved by raising the test server backlog;
the final clean browser run had no resource errors. These were not mistaken for a
Gemini or production-source failure.

## Intentional Differences

- Own identity and generated illustration, not the reference's logo/author image.
- Dedicated hands and markets routes, article-body summaries, bookmarks and health view.
- No copied long company biographies or curator essays; facts/evidence are linked.
- Company evolution uses categorical events plus separate detailed histories rather
  than reproducing the reference's exact combined duration-chart artwork.
- Reference mobile's broken one-word/character-wide titles are not reproduced.

## Follow-up Polish And Residual Risk

- Very dense networks still require zoom; phone context is presented in detail dialogs.
- Not every original publisher permits article extraction. Such stories are skipped,
  not expanded from a title. Source/index outages retain a visibly dated snapshot.
- GitHub queue delays and upstream outages cannot be guaranteed never to recur.
  Real failures remain visible and failure emails are not disabled.
- No login, synced cross-device bookmarks or private backend is implied by this static build.

## Implementation Checklist

- [x] Source and implementation desktop/mobile captured and compared together.
- [x] P0/P1/P2 issues fixed and post-fix captures inspected.
- [x] Required typography/layout/color/image/copy passes completed.
- [x] Primary interactions, empty states, data boundaries and browser errors checked.
- [x] Static export excludes dependencies, Git metadata and Python caches.

final result: passed

## Responsive Follow-up

Follow-up request: explicitly support phones, iPads and computers, including rotation.

- At 768 px the original 275 px rail reduced the news column to 493 px. Portrait
  tablet layouts now use the full column; company details remain available by tapping.
- Phone/tablet news filters wrap into deliberate rows. Touch inputs use 16 px text
  and main icon actions are 44 px; labeled tablet buttons are not forced into icon widths.
- Settings and navigation menus scroll within short landscape viewports. Mobile menu
  edges stay onscreen and tapping the same menu a second time now closes it.
- Safe-area insets and dynamic viewport height reserve room for device edges and
  bottom navigation. Mobile dialogs fill usable height without clipping close controls.
- Charts relayout on resize/rotation without losing the selected month or layout.
  The Figure evolution chart also redraws to its actual modal width.
- Ordinary charts permit native vertical touch scrolling; only the interactive
  relationship map captures pan/zoom gestures. Wide tables retain internal scrolling.
- Computer layouts remain fluid, including 2560 px width, without a page-wide maximum.

Verification used Playwright's WebKit engine with an iPad touch-emulation context,
not physical iOS hardware. Final WebKit checks covered all 13 routes at 320x568,
390x844, 568x320, 768x1024, 820x1180, 844x390, 1024x768, 1180x820 and 1366x1024:
117 route/viewport checks, zero document overflow, clipped company-filter labels,
or JavaScript errors. Chromium additionally passed 65 route/viewport checks across
568x320, 1280x800, 1440x900, 1920x1080 and 2560x1440.

Touch interactions checked: first/last menu bounds and dismissal, language settings
in a 568x320 landscape viewport, 320/568/768-wide company dialogs, and relationship
map rotation from 1024x768 to 768x1024. Month 2025-09 and cluster layout were preserved;
chart viewBox width updated to 768. The phone company chart updated to 340 px width.

Evidence: `output/playwright/responsive-ipad-comparison.png` puts the original and
revised 768x1024 Chromium captures side by side at density 1. Touch screenshots
`responsive-final-news-*.png` and `responsive-webkit-*.png` use density 2 and were
inspected separately; they are not treated as 1:1 pixel comparisons with density-1 shots.

Responsive follow-up result: passed.
