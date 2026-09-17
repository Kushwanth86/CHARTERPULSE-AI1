# MarineVessels Ingestion Policy

The normalized MarineVessels dataset contains 63,701 records.

Identity coverage:
- 26,611 records have both IMO and MMSI.
- 37,090 records have neither IMO nor MMSI.
- 5 duplicate IMO values affect 10 records.
- MMSI values are unique in the source.

Production ingestion policy:
- Preserve the normalized source dataset as reference data.
- Do not ingest records with ambiguous identity into the production `vessels` table.
- Do not ingest identifier-less records into the production `vessels` table in the initial load.
- Preserve duplicate/ambiguous records in an audit CSV and validation report.
- Keep the existing database constraints: `imo_number` unique and `mmsi` unique.
- Do not silently choose a winner among conflicting duplicate IMO records.
- Preserve missing physical fields as NULL.
- Do not infer cargo capacity or cargo compatibility from vessel type.
- Use `source = MarineVessels` and `provenance = PUBLIC_PROXY`.
- Supabase writes must be performed only by a dedicated loader after validation.
