# Tanker weekly change consistency audit — 2026 W41–W43

## Purpose and limits

This is a **source-text consistency screen**, not a validated market dataset. Reported route values and stated weekly changes were transcribed from the official Baltic Exchange report pages linked below. The audit compares each report's displayed end value with the prior report's displayed end value and checks whether that arithmetic agrees with the stated weekly change.

The official publisher pages are indexed and readable through search results, but automated requests from GitHub Actions returned a publisher-side **“Challenge Validation”** page rather than the report HTML. Therefore the raw HTML archive is **not complete**. This CSV is not a substitute for archived originals or independent confirmation from the publisher.

## Result

- 18 route/week comparisons reviewed (six routes across Weeks 41–43).
- 1 comparison matches the stated change (TD3C, Week 42).
- 17 comparisons do not reconcile from the displayed previous-week and current-week values.
- Treat every flagged value as **review required**. Do not use this screen alone to approve observations, train models, or publish market claims.
- Possible causes include transcription errors, source-page inconsistencies, differing assessment cut-offs, or changes calculated from a reference not represented by the prior report's displayed value. This audit does not determine which explanation is correct.

## Official sources

- [Tanker report – Week 40 (2 Oct 2026)](https://www.balticexchange.com/en/data-services/WeeklyRoundup/tanker/news/2026/tanker-report-week-40.html)
- [Tanker report – Week 41 (9 Oct 2026)](https://www.balticexchange.com/en/data-services/WeeklyRoundup/tanker/news/2026/tanker-report-week-41.html)
- [Tanker report – Week 42 (16 Oct 2026)](https://www.balticexchange.com/en/data-services/WeeklyRoundup/tanker/news/2026/tanker-report-week-42.html)
- [Tanker report – Week 43 (23 Oct 2026)](https://www.balticexchange.com/en/data-services/WeeklyRoundup/tanker/news/2026/tanker-report-week-43.html)

## Next acceptance criteria

1. Obtain the original report HTML through a publisher-accessible path and preserve the exact bytes, retrieval time, and SHA-256.
2. Re-transcribe the flagged values against those originals, ideally with a second independent pass.
3. Ask the publisher or use an independently licensed reference when the source's stated change does not reconcile with displayed values.
4. Keep unresolved rows quarantined from production forecasting inputs.
5. Only mark a row verified after its value, unit, route, reporting date, direction, and qualifier all pass review.
