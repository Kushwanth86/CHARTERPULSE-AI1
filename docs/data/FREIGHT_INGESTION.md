# Freight observation ingestion

Route-specific forecasts must start with observations from the **same assessed
route and vessel class**. A general index is not a route rate. Do not convert an
index point or a USD/day assessment to USD/MT without a documented, tested
transformation. Do not map a regional route onto Abbot Point or Achra merely
because it is geographically nearby.

## Suitable input sources

Prefer a licensed freight provider's route/vessel-class assessment or a recorded
market quote/fixture that actually refers to the route being modeled. The
[Baltic Exchange dry-bulk service](https://www.balticexchange.com/en/data-services/market-information0/dry-services.html)
publishes voyage assessments in USD per tonne and time-charter assessments in
USD per day. Its market-data access is subject to subscription/licence terms
([market-data access policy](https://www.balticexchange.com/en/data-services/Methodology/market-data.html)).
Its standard published routes do not, by themselves, establish an
Abbot Point → Achra assessment. Obtain a real quote or source assessment for
that lane, or leave the route forecast unavailable.

The [World Bank Pink Sheet](https://www.worldbank.org/en/research/commodity-markets)
is a public commodity-price dataset, not a dry-bulk route freight-rate feed.
Fuel/coal prices and broad dry-bulk indices may support separately labeled
contextual features, but must not be ingested as `freight_rate` USD/MT records.

## CSV schema

Use `scripts/data/ingest_freight_observations.py` to import a provider export or
a reviewed quote file. Required columns:

```csv
origin_unlocode,destination_unlocode,vessel_class,market_type,metric,value,unit,currency,observed_at,retrieved_at,source,source_record_id,source_reference,provenance
AUABP,INACH,Panamax,DRY_BULK_FREIGHT,freight_rate,29.75,USD/MT,USD,2026-10-20T12:00:00Z,2026-10-25T15:00:00Z,Example Provider,quote-unique-id,https://provider.example/quote/quote-unique-id,REAL
```

The row above is **schema illustration only, not a real rate**. Do not load it.
Replace it only with actual source-observed values and the corresponding
provider reference. A source row ID must be stable and unique within that source across repeat exports.
Both timestamps must include a timezone; the importer normalizes them to UTC. Retrieval cannot precede the observation timestamp.

For the current forecast engine, only `metric=freight_rate`, `unit=USD/MT`,
and `currency=USD` are accepted. Other units are rejected instead of being
converted silently. `origin_unlocode` and `destination_unlocode` are resolved
to exact IDs in `public.locations`; missing codes or ambiguous mappings stop
the import. `SIMULATED` and `FORECAST` provenance are not accepted as market
observations. Use `REAL` for direct source assessments, `USER_PROVIDED` for a
documented quote supplied by the user, or `PUBLIC_PROXY` only when the record
really is a proxy and its exact assessed route is preserved.

## Safe procedure

1. Apply `supabase/migrations/037_source_backed_freight_ingestion.sql` to the
   intended Supabase project.
2. Place the reviewed provider export in a private/local data directory. Do not
   commit licensed or commercially sensitive rate files.
3. Run a read-only dry run first:

   ```powershell
   .\.venv\Scripts\python.exe scripts/data/ingest_freight_observations.py --csv path\to\provider_export.csv
   ```

4. Confirm that all UN/LOCODEs resolve, units are USD/MT, timestamps and
   provider references are correct, and the source truly assesses the stated
   route. Only then run the same command with `--apply`.
5. Query `/api/v1/market/observations?origin_location_id=...&destination_location_id=...&vessel_class=Panamax&metric=freight_rate`
   and inspect `source`, `source_record_id`, `source_reference`, `provenance`,
   `observed_at`, `retrieved_at`, and `ingested_at`.
6. Generate the route/class forecast and validate the stored forecast's input
   provenance before using it in decision evaluation.

The importer is insert-only. Exact repeat imports are skipped, and conflicting
reuse of a provider record ID fails closed rather than silently overwriting
history. Batches already committed before a later batch fails are safe to retry:
the source identities make exact repeats idempotent.
