# Wingman — project guide for Claude Code

Wingman ("Never fantasy alone.") is a live fantasy-football companion web app. It is ONE app file,
`index.html` (HTML + CSS + JS), plus the brand asset files next to it (favicons, manifest, header/primary lockup SVGs —
light-background variants are swapped in by `html[data-theme=light]`). Never re-embed brand images as base64. It is hosted on GitHub Pages at
https://getwingman.github.io (served from the `main` branch, root). `wingman-connect-worker.js` is an optional
Cloudflare Worker (Yahoo OAuth, private-ESPN proxy, screenshot vision) — never put secrets in index.html.

The current version label is in Settings: `<span class="ver">vNN</span>` — bump it on every change.

## Tabs / modules
- **Matchups** (main): hero scoreboard, mirrored lineup table, Plays, low/high strip, mini matchup tiles, Bench.
  Modules are draggable (`<!--M:key-->` markers + `modWrap`/`bindMods`).
- Navigation: **Matchups** | **Radar** (tab `f`, marked BETA, `.betaf`) | **Lab** (tab `t`) | **Edge** (tab `e`, only after unlock) |
  **Survivor** | **Pick'em**. Swipe order: leagues → Radar → Lab → Edge → linked sheet modes. The phone bar must fit 6 tabs at 344px.
- **Radar** (`fdRender`): before any of the matchup's games start it shows a calm "Before kickoff" schedule (`.kfr`: kickoff
  slots with each side's starters) and projected scores; the play-by-play fields appear only once games are live/final.
- **Survivor** / **Pick'em** are sheet modes (`SHEETMODES`): hidden until the user links a Google Sheet from the
  connections page. NO pool data, member names or sheet IDs live in the page: everything is read from the linked sheet
  (`gvizCsv`, whole tab, `headers=0`, columns found by header name) and per-pool settings (`poolCfg`/`savePoolCfg`: whose
  entries, reuse rule, buy-in, payouts) are stored with the connection on the device. `resetPool` clears all state on
  unlink/switch. Survivor eligibility = `svCanUse(lane, team, week)` over the full pick history (`svUsed`), multi-pick cells
  (`svSplit`), eliminations; the planner may only offer teams that pass it. Pick'em parsing (`pkParse`) has no row cap and
  reports missing weeks / Picks-vs-Standings mismatches.
- **Lab**: "🏆 Rankings & IQ" board. Two different rankings, never one label: **Season** rank (history: all-play 45%,
  pts/wk 35%, record 20% — `computePower`) and projected **Strength** (best legal lineup per projected week through the
  league's final playoff week, `finalWeek`). Lineup IQ (efficiency) ≠ Start/Sit (share of right calls); awards and IQ need
  ≥3 completed weeks. Explicit end-of-season / no-projection states (never zeros). `wpBacktest` shows a calibration check.
  League Power Movement: `computePower` also builds `lg.ptrend` (Season rank after each completed week, records from that
  week's pairings via `weekPoints` → `[rid,pts,matchup_id]`, cache `wk2_`; last point = official rank) → Trend sparkline column
  + chips (biggest riser/faller over 3 weeks, outperforming roster = Season rank ≫ Strength rank, better than record).
  Board numbers: tabular Barlow, right-aligned; methodology lives in `data-tip`s (Season, Trend, Strength, 🏆 odds, IQ).
  Trades: **Trade partner matrix** (`R.prof`: each team's weakest starting position vs league average = need, best player
  outside its best lineup = surplus; `R.byP`: up to 3 packages per partner) — tap a manager to open the packages. Every trade
  card explains both sides (`explain()` → `whyTxt`: who enters each best lineup, who it pushes out, whether what's given was
  only bench depth, "fills their weakest spot"). 3-way trades stay as a side panel.
- **Edge** (tab `e`, chest icon in the Lab header, or `#edge`): locked per device. Password "edge" is checked against a
  SHA-256 hash (`EDGE_H`); only a token (`lm_edge_ok`) is stored; 🔒 `edgeLock()` relocks. It is a privacy curtain, not
  server security — everything is computed in the browser and nothing personal ships with the site. Edge shows every
  visible league side by side (`edgeLeagues()`: up to 4 on desktop, the selected one on phones): ⚡ Do this now (lineup
  swaps / dead starters / top claim, this week's numbers), ➕ Pickups that upgrade you (gain ≥0.5 pts/wk only; sortable by
  gain / FAAB / risk), 👀 Watchlist & stashes (no lineup gain: handcuffs, trending), 🗓 Roster alerts, 🔁 Streamers,
  🎯 Ideal lineup (collapsed by default).
- Lineups: `bestLineup(ids, slots, valueFn, prefer)` is the single EXACT optimizer (laminar greedy + branching over
  dual-position players, Hungarian for overlapping flexes; IDP slots supported). Fills every fillable slot; ties go to the
  lineup actually started. Used by strength, trades, pickups, Lineup IQ, start/sit and awards. Never replace it with a
  heuristic: tests/unit/optimizer.test.js checks it against brute force.
- Win-probability history (`recordWP` / `sparkWP`) records real model estimates only while players are live; persisted per
  league+week. The header chart is ALWAYS win % (0–100) from the first estimate; with too little history it shows a quiet
  waiting state (never a point-differential chart, never invented movement). Hover/tap shows time, WP and score margin.
- Simulations are seeded (`rng32`/`hash32` → `RND`), so identical inputs give identical odds. Heartbeat fires only when
  real points change. Header states: pregame (`hs-pre`: projections lead), live, final.
- Refresh is adaptive (`refreshDue`): chosen cadence while games are live, 15s just before kickoff, 60s otherwise;
  paused in background; per-league backoff (`retryAt`); stale week responses dropped. Errors shown to users go through
  `friendlyErr` (raw HTTP/URLs only in the console). Connection rows show Connected / Syncing / Needs attention /
  Access pending / Retrying / Disconnected; screenshot imports say they don't sync.

## Architecture
- Providers are adapters in `PROV` (sleeper, espn, yahoo, mfl, fleaflicker, manual = Custom Import). Each returns the
  normalized model: league{league:{name,roster_positions,settings,scoring_settings}, sc, rosters, users, mineRid}
  and `matchups(lg, week)`. Core UI must not depend on provider-specific shapes.
- Canonical player ids = Sleeper public player DB ids; `canon()` crosswalks ESPN/Yahoo/MFL/Fleaflicker ids
  (stable id first, then name+team+pos; never auto-merge ambiguous names).
- Scoring: `calcPts(stats, sc)` over normalized keys (derives FG buckets, points-allowed tiers, yardage bonuses).
  Provider-reported official points stay authoritative (see `display()`). Never hard-code fantasy point values.
- Win probability: `wpModel(a,b,dA,dB)`; signals in `buildSignals()`; Wingman Pulse in `sweatItems()/renderSweat()`.
- Live NFL data (ESPN scoreboard/summary, NFL stat feed) is provider-independent.

## Animations
- ONE engine: `playEventAnimation(kind, target, {age, side, rm})`. Live events and the Settings Animation Lab both use it.
  Live: cells carry `data-fx`; `applyFx()` re-applies after re-render with a negative delay (resume, never restart).
- Effects cover the full player cell; transient labels render in the fixed `#fxlayer` overlay (never clipped).
- First ~25s after load is a quiet warm-up (`quiet()`): no toasts/sounds/confetti/effects for pre-existing events.
- Respect `prefers-reduced-motion` (`.rm` static variant). No layout shift; rows stay 36px.

## Design rules
- Dense, desktop-first; header is one row (~47px); player rows 36px. Don't increase heights.
- Purple = me, cyan = opponent, green = live/positive, amber = pending, red = danger, gold = scoring/exceptional.
- Show, don't say: prefer visual signals (bars, intensity, position); exact numbers on hover.
- Typography: Inter (UI), Barlow Semi Condensed (scores/points). Light mode via `html[data-theme=light]` overrides.
- Watch for CSS class-name collisions (they caused past bugs: `.rv`, `.sep`, `.hd`, `.fx`, `.lg`, `.tlg`, `.rec`, `.stk`,
  `.up` on containers, `td.n b`). Grep before adding a short class name.

## Mobile rules
- Phones (≤760px): bottom tab bar (icon over label via `.tbi`/`.tbl` spans; must fit 5 tabs at 344px), header two rows.
- Touch sizing lives in `@media(pointer:coarse)` (phones, landscape phones, tablets) — never in width queries:
  inputs/selects 16px (prevents iOS focus-zoom), controls ≥34px, small links get an invisible `::after` hit area.
- Every `data-tip` must be readable by tap (global touch-tip handler); hover-only reveals are not allowed.
- Notch/home-indicator: `viewport-fit=cover` + `env(safe-area-inset-*)` on header, main, tab bar, toasts.
- Wide tables scroll inside their card; the Lab board pins `#` + Manager (`position:sticky`) on phones.
- Polling pauses while `document.hidden`; `pruneStore()` drops stale per-week caches (quota safety on iOS).
- Before first connection (`body.nolg`) the tab bar and empty week picker are hidden; pool-only users open their pool.

## Sheet layouts (v41+)
- Survivor (normalized): `Config` (key,value,type) · `Entries` (entry_id, participant, lane, is_our_entry) ·
  `Picks` (week, entry_id, team, picked_by; several rows = multi-pick week) · `Results` (week, team, opponent, game_day, result).
  Rules self-configure from Config (`svCfgFromSheet`: reuse, day rules incl. "pending", tie rule, missed-pick text, price,
  members, jackpot, current week); device settings override; "↺ Use the sheet's settings" clears overrides. Sheet results
  are authoritative for survival; ESPN adds scores/clocks/odds. Legacy "🏊 Swimlanes" sheets still parse.
- Pick'em (normalized): `WM_Config`, `WM_Games` (team_a/team_b are NOT home/away; spread_a + spread_source),
  `WM_Picks` (grades/points authoritative), `WM_Participants`, `WM_Tiebreakers`. Standings, cover rates, coverage
  (MISSING vs No Pick vs Hidden) and tiebreak winners are derived in the app (`pkSyncNormalized`). Lines: Sleeper live
  (locked at kickoff) → the sheet's verified line (`pkSheetLine`) → nothing; proxies are labeled.
- gviz: config (key/value) tabs are read raw (`headers=0`) and merged with a header-mode read; data tabs use
  `headers=1`; `objRows` re-infers blank labels from the schema. Unknown tab names return the FIRST tab, so validate.
- Survivor portfolio planner: per-entry eligibility (`svCanUse`) + day rules (`svDayRule`), "value later" from team ratings
  (`svRatings`/`svRatedP`) over the next 3 weeks (💎 save), field crowding. Plans are scored on the exact distribution of
  lives kept (`svDist`: enumerates game outcomes; both sides of one game can't both win): 📈 Most lives (greedy),
  🧺 Portfolio (local search over all entries maximizing E[log(1+lives)] minus save cost — hedges single upsets), 🛡 Safest
  spread. Each team shows 💥 lives lost if it loses; >50% of lives on one team with ≥12% upset risk = "⚠ stacked"; an
  "If this team loses" table compares plans. Rival overlap shows "not visible yet" (never 0%) when picks are unknown.
  Hero tokens use `.tokl` (NOT `.tlg`, which is the tiny team badge on player photos).
- Pick'em: you're identified automatically (`autoMember`: exactly one member whose id/display name matches a connected
  Sleeper username or your display name in a connected league; ambiguous → ask once). 🧭 You vs the pool table for the
  latest week where most picks are visible. Leans under 55% (`EDGE`) are muted "Toss-up" (no ★, no colored bar).
  ⬆ climb / 🛡 hold chips (top 3 games): value vs the field = P(cover) − expected pool share on that side (pool's
  historical favorite rate).
- Secret view (`MV.view="edge"`): 🎯 Ideal lineup (`idealBuild`/`idealHtml`) rebuilt on every visit from fresh
  projections, injury + practice status (players DB refreshed if >2h old), ESPN implied totals, season form, news and a
  matchup tilt; started games locked; solved with `bestLineup`. Then pickups.

## Tests
- `tests/run_all.sh index.html` (offline; mocks every API). Add a test with every fix. Fixtures must stay anonymized.

## Workflow
- Edit `index.html` in place; keep it single-file. Check the browser console for errors.
- Test desktop (~1500px) and phone (390px): no horizontal overflow, rows 36px, header height unchanged.
- Bump the version label, commit with a short descriptive message.
