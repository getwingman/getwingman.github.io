# Wingman regression tests

Everything runs offline: Sleeper, ESPN, Google Sheets and the Worker's Yahoo calls are mocked (`mock.py`, `fixtures/`).
Fixture pools are anonymized copies of the real sheet layouts (names replaced). The mock answers an unknown sheet tab
with the first tab, the way Google's gviz endpoint does.

    pip install playwright && python -m playwright install chromium
    WORKER=../wingman-connect-worker.js tests/run_all.sh index.html

| file | covers |
|---|---|
| unit/optimizer.test.js | exact lineup optimizer vs exhaustive brute force (standard, superflex, 2QB, overlapping flexes, IDP, dual-position players, ties, negatives, empty slots) |
| unit/worker.test.mjs | Yahoo OAuth login/callback/session/refresh, CORS, error redirects |
| qa60.py | nav, chips, rows, photos, red zone, bench order, Lab board, trades link, sheet linking |
| t80.py | Lineup IQ = brute force on every completed team-week, Season vs Strength, awards gating, playoff weeks, end of season |
| t81.py | Survivor eligibility (full history, rules, multi-pick, eliminations), pool privacy, unlinking, Pick'em full-season parsing |
| t82.py | pregame/live header states, win-probability history, seeded odds, heartbeat gating |
| t83.py | adaptive refresh, backoff, friendly errors, connection states, calibration check |
| t84.py | scoring across league settings, cross-league exposure, screenshot-import matching |
| t90.py | new sheet layouts: Survivor Config/Entries/Picks/Results (self-configuring rules, flagged entries, planner eligibility) and Pick'em WM_* (standings = sheet, tiebreaks, coverage, line precedence) |
| t91.py | ideal lineup: injury/practice discounts, Vegas totals, locks, brute-force optimality, rebuild on every visit |
| t72.py / t73.py / t70.py / mqa.py | phones & tablets: layout parity, light mode, storage, background polling, onboarding, touch, device matrix |
