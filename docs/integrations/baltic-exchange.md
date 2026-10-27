# Baltic Exchange freight-rate ingestion

This is an integration path for actual Baltic Exchange market observations. The
file named `MarketDataAPI.pdf` is API documentation only; it contains no rate
history to import. The adapter retrieves JSON from a configured, entitled
Baltic Exchange feed.

## Before running it

1. Confirm the Baltic Exchange subscription and API entitlement cover API
   retrieval, storage in CharterPulse, forecasting, and the intended display or
   commercial use. Do not use this adapter to bypass product licensing.
2. Create a feed in the Baltic Exchange portal using JSON and schema version
   `v1.3` (the provider manual says to choose the highest available version).
3. Add the actual market-data index sources required for the relevant freight
   market and vessel classes.
4. Obtain the API key and feed API identifier from the authenticated portal.
   Never place the API key in frontend code, a Git commit, a ticket, or chat.
5. Create an explicit route mapping only when a Baltic benchmark is truly
   equivalent to the corresponding CharterPulse origin/destination records.
   Do not infer a route mapping from a vague description. For example, the
   provider manual describes C5 as “Capesize West Australia to Qingdao”; do not
   map it to other locations just because the vessel family matches.

## Configure the local server environment

Add values to the repository-root `.env` file or the backend secret store.
The real `.env` file must not be committed.

```dotenv
BALTIC_EXCHANGE_API_KEY=YOUR_PRIVATE_API_KEY
BALTIC_EXCHANGE_FEED_ID=FDS_YOUR_FEED_IDENTIFIER
BALTIC_EXCHANGE_API_VERSION=v1.3
BALTIC_EXCHANGE_API_BASE_URL=https://api.balticexchange.com
BALTIC_EXCHANGE_ROUTE_MAP_JSON={"C5":{"origin_location_id":"REAL_ORIGIN_UUID","destination_location_id":"REAL_DESTINATION_UUID","vessel_class":"Capesize"}}
```

The C5 object above is a format example only. Replace the code and both UUID
values with actual provider and database identifiers. The origin and destination
must be different real location UUIDs, and the vessel class must be explicit.
The current model only imports voyage assessments reported in USD per metric
tonne. Rates in USD/day, container units, or other units are skipped rather than
converted or guessed.

Optional: set `BALTIC_EXCHANGE_STATE_FILE` to a durable local path. By default
the importer writes its last-successful-sync marker under
`~/.charterpulse/baltic_exchange_sync_state.json`.

## Run from the repository root

First run the parser and API fetch in dry-run mode:

```powershell
python scripts/import_baltic_exchange.py --dry-run --force
```

The output shows how many observations passed validation and why source rows
were skipped. It does not write to Supabase or advance sync state.

Review the route mapping and results. Then perform the import:

```powershell
python scripts/import_baltic_exchange.py --force
```

The script:
- calls `/{version}/feed/{feedApiIdentifier}/latestDatumChangeOn` first;
- avoids fetching the data endpoint when the source has not changed since the
  last successful import (unless `--force` is supplied);
- retrieves `/{version}/feed/{feedApiIdentifier}/data`;
- accepts only provider rows explicitly mapped to a CharterPulse route and
  reported in USD/MT;
- validates dates and finite positive values;
- records provenance as `REAL` and retains the provider code/date in
  `source_reference`;
- skips observations already imported with the same provider code/date;
- advances sync state only after a successful, non-empty import.

Use only one importer process per feed at a time. The current duplicate check
prevents routine repeat imports, but it is not a substitute for a database
unique constraint when multiple concurrent importers are used.

## Verify before forecast generation

Run:

```powershell
python -m pytest services/api/tests/unit/test_baltic_exchange.py
```

After import, query `market_observations` and confirm each observation has
`provenance = 'REAL'`, `metric = 'OCEAN_FREIGHT'`, `unit = 'USD/MT'`,
the expected origin/destination UUIDs, the intended vessel class, distinct
observation dates, and a `source_reference` beginning with
`baltic-exchange:`.

Passing import validation does not by itself make a source a valid operational
forecast. The benchmark route must match the procurement route; there must be
enough distinct dates; and the resulting forecast must pass existing evidence
and out-of-sample quality checks. Missing or non-equivalent routes must remain
unavailable rather than being estimated from a convenient benchmark.
