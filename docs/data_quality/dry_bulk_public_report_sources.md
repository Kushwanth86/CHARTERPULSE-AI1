# Existing public dry-bulk reports — source-backed reference dataset

This dataset transcribes only values explicitly present in two user-provided documents:

1. **Commodity and Freight Market Insider, Week 44 (Aryacorp), dated 26 October 2026**. Most freight observations are Friday 23 October 2026 closes. The fixture list covers fixtures reported during 19–23 October. See pages 1–3.
2. **BRS Group Annual Review 2026**, Dry Bulk section, especially page 73. The historical Panamax observations refer to calendar year 2025.

## Provenance classes

- `PUBLIC_PROXY`: published index or segment/route benchmark. It is not an exact route quote.
- `PUBLIC_FIXTURE`: a reported fixture with route, vessel size and time-charter rate. It is not transferable as a quote for a different route/cargo.
- `HISTORICAL_CONTEXT`: historical market-review figures or commentary. Not a current market observation.
- No row in this file is labelled `REAL`, `USER_PROVIDED`, or forecast-eligible.

## Important interpretation limits

- Baltic Dry Index, Baltic Panamax Index and other index points are not freight prices in USD/tonne or USD/day.
- Segment average time-charter earnings are broad market references, not voyage rates.
- The Aryacorp Panamax fixtures are on routes such as East Coast Australia, North Pacific, Indonesia and US East Coast–India. They do not match Dehdadi–Annaba or a limestone shipment.
- The C5 and C3 values are Capesize route assessments. They must not be applied to Panamax.
- BRS's 2025 Panamax FFA average is a paper-market measure, not a physical fixture.
- The BRS report contains historical market analysis and an outlook; it does not supply a verified Dehdadi–Annaba limestone quotation.

## Integration policy

Use these records for market context, benchmark visualisations and source-aware model features only after the application's schema and feature contracts are checked. Do not let these records satisfy the application's requirement for a route-matched verified observation. In particular, do not populate the procurement Freight P50, risk score, or recommendation for the Dehdadi–Annaba request from these broad benchmarks.

## Source attribution

- Aryacorp: *Commodity and Freight Market Insider*, Week 44, 2026, pp. 1–3. The report cites Baltic Exchange/Reuters/The Edge Malaysia and other public sources and disclaims warranty of accuracy or completeness.
- BRS Group: *Annual Review 2026*, Dry Bulk section, p. 73.

This is a manual transcription of the supplied PDFs. Preserve the original documents alongside this file when using it operationally; do not represent this CSV as a licensed raw feed or an official Baltic Exchange data export.
