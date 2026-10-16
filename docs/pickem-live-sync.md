# Wingman Pick'em: one-time live Sleeper connection

## What's already done
- The Pick'em sheet is now **input-only**: `WM_Games` (teams, game IDs and verified pool spreads), `WM_Picks` (submitted picks), `WM_Participants`, `WM_Tiebreakers` (guesses), and `WM_Config`.
- Wingman pulls ESPN NFL scoreboard data for all completed/current weeks and computes winners, ATS grades and standings in its own JavaScript. It does **not** read Google Sheet grades, scores, or standings.
- Historical W1–W4 results are preserved as a fixed migration-only outcome map because the pool's historical locked spreads were not captured. The full pre-migration sheet backup exists separately.
- A protected, read-only `GET /pickem/season` endpoint has been added to `wingman-connect-worker.js`. It retrieves authenticated Sleeper picks, discloses each game's picks only when Sleeper marks it complete, and never uses Sleeper's misleading `outcome` field as an ATS score.

## What still needs deployment
The source is committed, **not deployed to the existing Cloudflare Worker by a GitHub commit**. Until these steps are complete, the authenticated reader is unavailable, and Week 5+ member picks cannot update automatically.

1. In Cloudflare Workers & Pages, open the Worker serving `https://connect.getwingman.workers.dev`. Review the updated `wingman-connect-worker.js` from this repo, then deploy it to that Worker, preserving its existing OAuth, ESPN, and AI configuration.
2. Add these as **Cloudflare Worker secrets / configuration**, never in `index.html`, the Google Sheet, GitHub source, or a chat message:
   - `SLEEPER_TOKEN`: an authorized Sleeper session JWT obtained from your own Sleeper account (treat like a password).
   - `WM_PICKEM_VIEW_KEY`: a separately generated random viewer key, at least 24 characters. This is **not** your Sleeper token.
   - `WM_PICKEM_POOL_ID`: `1392587441361129472`.
   - Retain `ALLOWED_ORIGIN=https://getwingman.github.io` and existing Worker secrets.
3. Open Wingman → Settings/Connections → Pick'em → **Use Sleeper pool**. Unlock its reader using your **viewer key**, not your Sleeper session token. The key stays in the current browser tab's session storage.
4. Confirm the reader shows identified entries and finalized games and that their mapped picks match your original pool. No nonfinal manager picks should be revealed.
5. Confirm ATS points after an ESPN final **only if** its original Sleeper pool-locked spread has been independently verified; otherwise show pending. Never substitute live market odds for the pool's locked line.

## Limitations & QA
- Unauthenticated ESPN data cannot reveal private Sleeper pool picks.
- Sleeper's Pick'em GraphQL surface is undocumented and subject to change; verify the deployed Worker against your actual pool. The source test uses mocked upstream responses and does **not** establish live account access.
- The public Sleeper REST roster-to-user mapping may not work for every Pick'em pool. The Worker returns an explicit failure rather than inventing a mapping if it cannot resolve entries.
- Weeks without captured pool-locked ATS spreads remain **ungraded**, even when final NFL scores are available. Your sheet currently has a verified spread set for Week 5, but Week 6+ spreads were not captured at migration time.
- Avoid exposing or sharing any Sleeper token in chat. Rotate it if it is ever disclosed.

QA commands (in repo clone): `bash tests/run_all.sh index.html` or `node tests/unit/pickem_refresh.test.js index.html` and `node tests/unit/pickem_worker.test.js`.
