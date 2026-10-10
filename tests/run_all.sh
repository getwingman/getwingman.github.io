#!/bin/bash
# Wingman regression suite. Usage: tests/run_all.sh <path-to-index.html>
H=$(cd "$(dirname "$1")" && pwd)/$(basename "$1"); D=$(cd "$(dirname "$0")" && pwd); O=$(mktemp -d); cd "$D"
run(){ echo "=== $1"; shift; "$@" 2>&1 | grep -E "^(PASS|FAIL)|passed|FAILED" ; }
run "optimizer vs brute force" node unit/optimizer.test.js "$H"
cp "${WORKER:-$(dirname "$H")/wingman-connect-worker.js}" unit/worker.mjs 2>/dev/null; run "worker OAuth" node unit/worker.test.mjs
run "v38 features + desktop/phone" python3 qa60.py file://$H . $O
run "Lab: rankings, IQ, playoffs" python3 t80.py file://$H $O
run "Survivor eligibility, pools, privacy" python3 t81.py file://$H $O
run "header states, WP history, stable odds" python3 t82.py file://$H $O
run "refresh cadence, backoff, errors, calibration" python3 t83.py file://$H $O
run "scoring, exposure, import matching" python3 t84.py file://$H $O
run "mobile: desktop parity, light, storage, polling, onboarding" python3 t72.py file://$H file://${BASE:-$H} $O
run "new sheet layouts: Survivor Config/Entries/Picks/Results, Pick'em WM_*" python3 t90.py file://$H $O
run "ideal lineup (secret view)" python3 t91.py file://$H $O
run "touch interactions" python3 t70.py file://$H
run "v42: trade partners, power movement, Edge pickups, Survivor portfolio, Radar pregame, 6 tabs" python3 t92.py file://$H $O
run "v43 mobile: slot pills, full names, Lab strip, one Trades module" python3 t93.py file://$H $O
