# Production Readiness Audit — 2026-10-28

## Scope and evidence

This audit combines repository/CI inspection with read-only checks against the connected Supabase project and Vercel production deployment. It is not a substitute for a signed-in browser session or an authorized live market-data provider test.

## Status by capability

| Capability | Status | Evidence / remaining work |
| --- | --- | --- |
| Frontend production build | PASS | GitHub Actions production build passed for the latest mainline change; Vercel production deployment is READY. |
| Backend unit and API contract tests | PASS (automated) | Repository pytest job passes. Tests use dependency overrides/mocks for some authenticated flows. |
| Frontend regression tests | PASS (automated) | Node/tsx regression suite passes. |
| Authentication and row ownership | PASS (database policy checks) | Auth ownership/RLS migration is applied; Supabase security advisor returned no findings. Full real-user browser workflow remains unverified. |
| Forecast row safety | PASS (basic invariants) | Live rows have ordered p10 <= p50 <= p90, non-null quantiles, confidence in [0,1], and no negative forecast values. |
| Forecast accuracy | BLOCKED / INCOMPLETE | 21 forecast rows exist, but only one has MAE/RMSE/sMAPE, none has interval coverage, and model_evaluations contains zero rows. Real historical/current benchmark data and rolling backtests are still needed. |
| Market-data freshness and provenance | BLOCKED | market_observations has 6 rows, all from SIH_TEST_SCENARIO (Aug 1–Sep 5, 2026). No Baltic Exchange observations are present. |
| Baltic Exchange ingestion code | IMPLEMENTED; live validation BLOCKED | Host restrictions, route mapping, input validation, and concurrency-safe idempotency are in main. A valid provider entitlement/credential and verified route mapping are needed for a genuine feed test. |
| Database performance | IMPROVED | Added indexes for the 10 foreign-key columns flagged by the Supabase performance advisor. Verified all 10 indexes exist. The advisor now reports only informational unused-index findings; do not drop these without workload evidence. |
| Production application errors | NO CLUSTERS REPORTED | Vercel runtime error aggregation reported no runtime errors in the last 24 hours. Raw runtime logs for 24 hours were unavailable under the current plan retention; use a short recent window for log-level verification. |
| Backend latency/resource capacity | NOT VERIFIED | Render workspace selection is required before service metrics/logs can be queried; do not infer performance from frontend deployment status alone. |
| End-to-end signed-in journey | PARTIAL | Automated API and frontend contract tests exist, but tests/e2e/decision_workflow has no runnable end-to-end test yet. A real signed-in browser test and authorized production-safe test account are still needed. |

## Live database snapshot

Checked 2026-10-28:
- market_observations: 6 total; 0 with Baltic source; all six are labelled SIH_TEST_SCENARIO.
- freight_forecasts: 21 total.
- model_evaluations: 0 rows.
- decision_runs: 110 rows.
- Forecast quantile ordering violations: 0.
- Confidence range violations: 0.
- Missing quantiles: 0.
- Negative forecast values: 0.
- Forecast generation timestamps range from 2026-09-09 to 2026-10-18, so freshness must be assessed against source observation timestamps before production decisions rely on them.

## Changes shipped during this audit

- Merged PR #42: made Baltic Exchange imports concurrency-safe and idempotent; verified its unique index is present in Supabase.
- Merged PR #43: added ten foreign-key covering indexes; verified all ten indexes exist in Supabase.
- Both PRs passed backend and frontend regression/build jobs; the latest production deployment for the index change reached READY.

## Release blockers to reach a credible ~90% readiness

1. Configure authorized provider access through the appropriate secret manager (never commit or paste credentials into source/chat).
2. Confirm provider route mappings and import genuine current/historical observations; verify units, timestamps, provenance, and deduplication.
3. Add a rolling/expanding-window backtest using actual observations and record MAE, RMSE, sMAPE, interval coverage, and baseline comparison in model_evaluations.
4. Add a runnable end-to-end test for sign-in, cargo/procurement input, route/forecast selection, decision evaluation, and authorization boundaries.
5. Select the correct Render workspace to verify backend service health, recent logs, latency, and resource metrics.
6. Run a production-safe signed-in smoke test and verify error handling/failure recovery for unavailable data providers.

## Important caveat

A successful CI run, clean security advisor, or READY deployment does not establish that forecasts are accurate or that a third-party live feed is operational. Keep these capabilities marked incomplete until the above evidence exists.
