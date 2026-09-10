import type { CargoRequirement, Country, FreightForecast, MarketObservation, Port } from "../api";

export const REFERENCE_COUNTRIES: Country[] = [
  { id: "ref-in", name: "India", iso2: "IN", iso3: "IND", country_code: "IN" },
  { id: "ref-au", name: "Australia", iso2: "AU", iso3: "AUS", country_code: "AU" },
  { id: "ref-id", name: "Indonesia", iso2: "ID", iso3: "IDN", country_code: "ID" },
  { id: "ref-za", name: "South Africa", iso2: "ZA", iso3: "ZAF", country_code: "ZA" },
  { id: "ref-br", name: "Brazil", iso2: "BR", iso3: "BRA", country_code: "BR" },
  { id: "ref-cn", name: "China", iso2: "CN", iso3: "CHN", country_code: "CN" },
  { id: "ref-us", name: "United States", iso2: "US", iso3: "USA", country_code: "US" },
  { id: "ref-ru", name: "Russia", iso2: "RU", iso3: "RUS", country_code: "RU" },
  { id: "ref-ca", name: "Canada", iso2: "CA", iso3: "CAN", country_code: "CA" },
  { id: "ref-co", name: "Colombia", iso2: "CO", iso3: "COL", country_code: "CO" },
  { id: "ref-mz", name: "Mozambique", iso2: "MZ", iso3: "MOZ", country_code: "MZ" },
  { id: "ref-ph", name: "Philippines", iso2: "PH", iso3: "PHL", country_code: "PH" },
  { id: "ref-vn", name: "Vietnam", iso2: "VN", iso3: "VNM", country_code: "VN" },
  { id: "ref-jp", name: "Japan", iso2: "JP", iso3: "JPN", country_code: "JP" },
  { id: "ref-kr", name: "South Korea", iso2: "KR", iso3: "KOR", country_code: "KR" },
  { id: "ref-tr", name: "Türkiye", iso2: "TR", iso3: "TUR", country_code: "TR" },
  { id: "ref-ua", name: "Ukraine", iso2: "UA", iso3: "UKR", country_code: "UA" },
  { id: "ref-nl", name: "Netherlands", iso2: "NL", iso3: "NLD", country_code: "NL" },
  { id: "ref-gb", name: "United Kingdom", iso2: "GB", iso3: "GBR", country_code: "GB" },
  { id: "ref-de", name: "Germany", iso2: "DE", iso3: "DEU", country_code: "DE" },
];

const port = (id: string, name: string, country: string, unlocode: string, latitude: number, longitude: number): Port => ({
  id, name, location_id: id, unlocode, latitude, longitude, source: "Frontend bulk-port reference", provenance: "PUBLIC_PROXY",
});

export const REFERENCE_PORTS: Port[] = [
  port("ref-in-prt", "Paradip", "IN", "INPRT", 20.2667, 86.7000),
  port("ref-in-vtz", "Visakhapatnam", "IN", "INVTZ", 17.6868, 83.2185),
  port("ref-in-hld", "Haldia", "IN", "INHAL", 22.0253, 88.0698),
  port("ref-in-dmq", "Dhamra", "IN", "INDMQ", 20.8070, 86.9525),
  port("ref-in-ggv", "Gangavaram", "IN", "INGGV", 17.6177, 83.2194),
  port("ref-in-kak", "Kakinada", "IN", "INKAK", 16.9891, 82.2475),
  port("ref-in-kri", "Krishnapatnam", "IN", "INKRI", 14.2456, 80.1245),
  port("ref-in-tut", "Tuticorin", "IN", "INTUT", 8.7642, 78.1348),
  port("ref-au-ncl", "Newcastle", "AU", "AUNTL", -32.9283, 151.7817),
  port("ref-au-phr", "Port Hedland", "AU", "AUPHE", -20.3100, 118.5770),
  port("ref-au-hay", "Hay Point", "AU", "AUHPT", -21.2910, 149.3030),
  port("ref-au-gla", "Gladstone", "AU", "AUGLT", -23.8427, 151.2550),
  port("ref-id-tan", "Tanjung Bara", "ID", "IDTBR", 0.0550, 117.5000),
  port("ref-id-sor", "Sorong", "ID", "IDSOQ", -0.8762, 131.2558),
  port("ref-id-jkt", "Jakarta", "ID", "IDJKT", -6.1040, 106.8820),
  port("ref-za-rbv", "Richards Bay", "ZA", "ZARCB", -28.7960, 32.0380),
  port("ref-za-sld", "Saldanha Bay", "ZA", "ZASDB", -33.0100, 17.9450),
  port("ref-za-dbn", "Durban", "ZA", "ZADUR", -29.8587, 31.0218),
  port("ref-br-ita", "Itaguaí", "BR", "BRITG", -22.9100, -43.8300),
  port("ref-br-tub", "Tubarão", "BR", "BRTUB", -20.2900, -40.2400),
  port("ref-br-pnt", "Ponta da Madeira", "BR", "BRPDM", -2.5700, -44.3700),
  port("ref-cn-qin", "Qingdao", "CN", "CNTAO", 36.0671, 120.3826),
  port("ref-cn-ntg", "Nantong", "CN", "CNNTG", 31.9800, 120.8800),
  port("ref-cn-bao", "Baoshan", "CN", "CNBAS", 31.3800, 121.4900),
  port("ref-us-npo", "Newport News", "US", "USNNS", 36.9660, -76.4400),
  port("ref-us-hou", "Houston", "US", "USHOU", 29.7300, -95.3500),
  port("ref-us-nor", "Norfolk", "US", "USORF", 36.8508, -76.2859),
  port("ref-ru-nov", "Novorossiysk", "RU", "RUNVS", 44.7200, 37.7700),
  port("ref-ru-vos", "Vostochny", "RU", "RUVYP", 42.7600, 133.0800),
  port("ref-co-cve", "Puerto Bolivar", "CO", "COBUN", 11.7000, -71.3500),
  port("ref-mz-bia", "Beira", "MZ", "MZBEW", -19.8400, 34.8400),
  port("ref-mz-nac", "Nacala", "MZ", "MZMNC", -14.4600, 40.6900),
  port("ref-ca-ham", "Hamilton", "CA", "CAHAM", 43.2950, -79.8500),
  port("ref-ph-sjn", "Subic Bay", "PH", "PHSFS", 14.7950, 120.2700),
  port("ref-vn-vta", "Vung Tau", "VN", "VNVUT", 10.4110, 107.1360),
  port("ref-jp-kob", "Kobe", "JP", "JPUKB", 34.6901, 135.1955),
  port("ref-kr-poh", "Pohang", "KR", "KRKPO", 35.9900, 129.3650),
  port("ref-tr-isk", "Iskenderun", "TR", "TRISK", 36.5800, 36.1700),
  port("ref-ua-ods", "Odesa", "UA", "UAODS", 46.4825, 30.7233),
  port("ref-nl-rtm", "Rotterdam", "NL", "NLRTM", 51.9244, 4.4777),
  port("ref-gb-ims", "Immingham", "GB", "GBIMM", 53.6120, -0.2220),
  port("ref-de-ham", "Hamburg", "DE", "DEHAM", 53.5511, 9.9937),
];

export const REFERENCE_MATERIALS = [
  "Coking Coal", "Thermal Coal", "Iron Ore", "Limestone", "Flux", "Manganese Ore", "Petroleum Coke", "Fertilizer", "Grain"
];

export const REFERENCE_CARGO_TYPES = [
  { id: "DRY_BULK", label: "Bulk Carrier / Gearless", meta: "DRY_BULK" },
  { id: "DRY_BULK_PANAMAX", label: "Panamax", meta: "DRY_BULK · vessel class" },
  { id: "DRY_BULK_CAPESIZE", label: "Capesize", meta: "DRY_BULK · vessel class" },
  { id: "DRY_BULK_HANDYSIZE", label: "Handysize", meta: "DRY_BULK · vessel class" },
];

export const REFERENCE_FORECAST: FreightForecast = {
  id: "frontend-reference-freight-2026-09", origin_location_id: "ref-au-phr", destination_location_id: "ref-in-vtz", vessel_class: "Panamax",
  p10: 30.4, p50: 32.2, p90: 34.6, baseline: 32.2, model_name: "frontend_reference_curve", model_version: "1.0",
  mae: 1.8, rmse: 2.1, smape: 5.9, interval_coverage: null, confidence: 0.62, provenance: "PUBLIC_PROXY", generated_at: "2026-09-10T00:00:00Z",
};

const refMarket = (id: string, metric: string, value: number, unit: string, date: string, source: string): MarketObservation => ({
  id, market_type: "PUBLIC_REFERENCE", metric, value, unit, currency: unit.includes("USD") ? "USD" : undefined, observed_at: `${date}T00:00:00Z`, source, source_reference: "FRONTEND_REFERENCE", provenance: "PUBLIC_PROXY",
});

export const REFERENCE_MARKET_OBSERVATIONS: MarketObservation[] = [
  refMarket("ref-bdi-1", "Baltic Dry Index", 2926, "INDEX", "2026-08-25", "Public BDI benchmark"),
  refMarket("ref-bdi-2", "Baltic Dry Index", 3056, "INDEX", "2026-08-26", "Public BDI benchmark"),
  refMarket("ref-bdi-3", "Baltic Dry Index", 3107, "INDEX", "2026-08-27", "Public BDI benchmark"),
  refMarket("ref-bdi-4", "Baltic Dry Index", 3186, "INDEX", "2026-08-28", "Public BDI benchmark"),
  refMarket("ref-bdi-5", "Baltic Dry Index", 3331, "INDEX", "2026-09-02", "Public BDI benchmark"),
  refMarket("ref-bdi-6", "Baltic Dry Index", 3584, "INDEX", "2026-09-08", "Public BDI benchmark"),
  refMarket("ref-vlsfo-1", "Singapore VLSFO", 817, "USD/MT", "2026-08-25", "Public bunker benchmark"),
  refMarket("ref-vlsfo-2", "Singapore VLSFO", 781, "USD/MT", "2026-08-26", "Public bunker benchmark"),
  refMarket("ref-vlsfo-3", "Singapore VLSFO", 770.5, "USD/MT", "2026-08-27", "Public bunker benchmark"),
  refMarket("ref-vlsfo-4", "Singapore VLSFO", 842, "USD/MT", "2026-09-07", "Public bunker benchmark"),
  refMarket("ref-vlsfo-5", "Singapore VLSFO", 842, "USD/MT", "2026-09-08", "Public bunker benchmark"),
  refMarket("ref-pmx-1", "Panamax Freight Reference", 28.4, "USD/MT", "2026-09-01", "Frontend freight reference"),
  refMarket("ref-pmx-2", "Panamax Freight Reference", 30.1, "USD/MT", "2026-09-05", "Frontend freight reference"),
  refMarket("ref-pmx-3", "Panamax Freight Reference", 31.5, "USD/MT", "2026-09-08", "Frontend freight reference"),
];

export const REFERENCE_CARGO_ROWS: CargoRequirement[] = [];
