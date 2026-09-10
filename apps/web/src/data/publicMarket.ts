export type PublicMarketPoint = {
  date: string;
  metric: string;
  value: number;
  unit: string;
  currency?: string;
  source: string;
  sourceUrl: string;
  provenance: "PUBLIC_PROXY";
};

// Publicly visible reference observations. These are not represented as direct exchange/API feeds.
// Keep the provenance PUBLIC_PROXY so the UI never implies a paid live market feed.
export const PUBLIC_MARKET_BASELINE: PublicMarketPoint[] = [
  { date: "2026-08-25", metric: "Baltic Dry Index", value: 2926, unit: "INDEX", source: "Investing.com historical BDI", sourceUrl: "https://sa.investing.com/indices/baltic-dry-historical-data", provenance: "PUBLIC_PROXY" },
  { date: "2026-08-26", metric: "Baltic Dry Index", value: 3056, unit: "INDEX", source: "Investing.com historical BDI", sourceUrl: "https://sa.investing.com/indices/baltic-dry-historical-data", provenance: "PUBLIC_PROXY" },
  { date: "2026-08-27", metric: "Baltic Dry Index", value: 3107, unit: "INDEX", source: "Investing.com historical BDI", sourceUrl: "https://sa.investing.com/indices/baltic-dry-historical-data", provenance: "PUBLIC_PROXY" },
  { date: "2026-08-28", metric: "Baltic Dry Index", value: 3186, unit: "INDEX", source: "Investing.com historical BDI", sourceUrl: "https://sa.investing.com/indices/baltic-dry-historical-data", provenance: "PUBLIC_PROXY" },
  { date: "2026-09-01", metric: "Baltic Dry Index", value: 3157, unit: "INDEX", source: "Investing.com historical BDI", sourceUrl: "https://sa.investing.com/indices/baltic-dry-historical-data", provenance: "PUBLIC_PROXY" },
  { date: "2026-09-02", metric: "Baltic Dry Index", value: 3331, unit: "INDEX", source: "Investing.com historical BDI", sourceUrl: "https://sa.investing.com/indices/baltic-dry-historical-data", provenance: "PUBLIC_PROXY" },
  { date: "2026-09-03", metric: "Baltic Dry Index", value: 3488, unit: "INDEX", source: "Investing.com historical BDI", sourceUrl: "https://sa.investing.com/indices/baltic-dry-historical-data", provenance: "PUBLIC_PROXY" },
  { date: "2026-09-04", metric: "Baltic Dry Index", value: 3628, unit: "INDEX", source: "Investing.com historical BDI", sourceUrl: "https://sa.investing.com/indices/baltic-dry-historical-data", provenance: "PUBLIC_PROXY" },
  { date: "2026-09-07", metric: "Baltic Dry Index", value: 3575, unit: "INDEX", source: "Investing.com historical BDI", sourceUrl: "https://sa.investing.com/indices/baltic-dry-historical-data", provenance: "PUBLIC_PROXY" },
  { date: "2026-09-08", metric: "Baltic Dry Index", value: 3584, unit: "INDEX", source: "Investing.com historical BDI", sourceUrl: "https://sa.investing.com/indices/baltic-dry-historical-data", provenance: "PUBLIC_PROXY" },
  { date: "2026-08-25", metric: "Singapore VLSFO", value: 817, unit: "USD/MT", currency: "USD", source: "Ship & Bunker Singapore", sourceUrl: "https://www.shipandbunker.com/prices/apac/sea/sg-sin-singapore", provenance: "PUBLIC_PROXY" },
  { date: "2026-08-26", metric: "Singapore VLSFO", value: 781, unit: "USD/MT", currency: "USD", source: "Ship & Bunker Singapore", sourceUrl: "https://www.shipandbunker.com/prices/apac/sea/sg-sin-singapore", provenance: "PUBLIC_PROXY" },
  { date: "2026-08-27", metric: "Singapore VLSFO", value: 770.5, unit: "USD/MT", currency: "USD", source: "Ship & Bunker Singapore", sourceUrl: "https://www.shipandbunker.com/prices/apac/sea/sg-sin-singapore", provenance: "PUBLIC_PROXY" },
  { date: "2026-08-28", metric: "Singapore VLSFO", value: 784.5, unit: "USD/MT", currency: "USD", source: "Ship & Bunker Singapore", sourceUrl: "https://www.shipandbunker.com/prices/apac/sea/sg-sin-singapore", provenance: "PUBLIC_PROXY" },
  { date: "2026-08-31", metric: "Singapore VLSFO", value: 812.5, unit: "USD/MT", currency: "USD", source: "Ship & Bunker Singapore", sourceUrl: "https://www.shipandbunker.com/prices/apac/sea/sg-sin-singapore", provenance: "PUBLIC_PROXY" },
  { date: "2026-09-01", metric: "Singapore VLSFO", value: 838, unit: "USD/MT", currency: "USD", source: "Ship & Bunker Singapore", sourceUrl: "https://www.shipandbunker.com/prices/apac/sea/sg-sin-singapore", provenance: "PUBLIC_PROXY" },
  { date: "2026-09-02", metric: "Singapore VLSFO", value: 856, unit: "USD/MT", currency: "USD", source: "Ship & Bunker Singapore", sourceUrl: "https://www.shipandbunker.com/prices/apac/sea/sg-sin-singapore", provenance: "PUBLIC_PROXY" },
  { date: "2026-09-03", metric: "Singapore VLSFO", value: 860.5, unit: "USD/MT", currency: "USD", source: "Ship & Bunker Singapore", sourceUrl: "https://www.shipandbunker.com/prices/apac/sea/sg-sin-singapore", provenance: "PUBLIC_PROXY" },
  { date: "2026-09-04", metric: "Singapore VLSFO", value: 848, unit: "USD/MT", currency: "USD", source: "Ship & Bunker Singapore", sourceUrl: "https://www.shipandbunker.com/prices/apac/sea/sg-sin-singapore", provenance: "PUBLIC_PROXY" },
  { date: "2026-09-07", metric: "Singapore VLSFO", value: 842, unit: "USD/MT", currency: "USD", source: "Ship & Bunker Singapore", sourceUrl: "https://www.shipandbunker.com/prices/apac/sea/sg-sin-singapore", provenance: "PUBLIC_PROXY" },
  { date: "2026-07-31", metric: "Australian premium coking coal", value: 218.6, unit: "USD/MT", currency: "USD", source: "IndexBox public market summary", sourceUrl: "https://www.indexbox.io/blog/coking-coal-prices-surge-in-august-on-china-demand-and-supply-shortages/", provenance: "PUBLIC_PROXY" },
  { date: "2026-08-28", metric: "Australian premium coking coal", value: 267.1, unit: "USD/MT", currency: "USD", source: "IndexBox public market summary", sourceUrl: "https://www.indexbox.io/blog/coking-coal-prices-surge-in-august-on-china-demand-and-supply-shortages/", provenance: "PUBLIC_PROXY" }
];

export const PUBLIC_VESSEL_REFERENCES = [
  { className: "Panamax", vessel: "MV FAIR LADY", dwt: 76608, loa: 224.98, beam: 32.24, draft: 14.446, fuel: 31.3, source: "Eastmed published vessel particulars", sourceUrl: "https://www.eastmed.gr/bulk-carriers-panamax/" },
  { className: "Capesize", vessel: "MV PROTI", dwt: 182608, loa: 292, beam: 45, draft: 18.18, fuel: 41.5, source: "Eastmed published vessel particulars", sourceUrl: "https://www.eastmed.gr/bulk-carriers-capesize/" },
  { className: "Handysize", vessel: "Baltic 38 reference", dwt: 38200, loa: 180, beam: 29.8, draft: 10.538, fuel: 26, source: "Baltic Exchange Handysize benchmark", sourceUrl: "https://www.balticexchange.com/en/data-services/market-information0/dry-services.html/1000" },
  { className: "Handysize", vessel: "Edward Oldendorff", dwt: 38691, loa: 179.9, beam: 30, draft: 10.5, fuel: 17.9, source: "Deltamarin vessel reference", sourceUrl: "https://deltamarin.com/app/uploads/pregenerate_pdf/edward-oldendorff.pdf" }
];
