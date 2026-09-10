import { REFERENCE_CARGO_ROWS, REFERENCE_COUNTRIES, REFERENCE_FORECAST, REFERENCE_MARKET_OBSERVATIONS, REFERENCE_PORTS } from "./data/referenceData";

const API_BASE = "http://127.0.0.1:8000";

export const TEST_CARGO_ID = "ca16e396-bacf-49b3-a06f-c4b9373dd26b";
export const TEST_FORECAST_ID = "6e7e8284-9b73-49b1-9767-30f536a7911a";

export interface DecisionResponse { decision_run_id: string | null; decision_status: string; recommendation: string; cargo_quantity_mt: number; currency: string; forecast_p10: number; forecast_p50: number; forecast_p90: number; now_expected_freight_cost: number; now_p90_freight_cost: number; wait_conservative_rate: number; wait_conservative_cost: number; wait_cost_difference: number; wait_cost_difference_per_mt: number; probability_now_exceeds_baseline: number; risk_score: number; provenance: string; model_name: string | null; forecast_id: string; rationale: string[]; warnings: string[]; generated_at: string; }
export interface HumanDecisionResponse { id: string; decision_run_id: string; action: string; modified_parameters: Record<string, unknown>; reason: string | null; decided_at: string; actor_reference: string | null; provenance: string; }
export interface Country { id: string; name: string; code?: string; country_code?: string; iso2?: string; iso3?: string; [key: string]: unknown; }
export interface Port { id: string; name: string; location_id: string; unlocode?: string | null; latitude?: number | null; longitude?: number | null; source?: string | null; provenance?: string | null; max_draft_m?: number | null; max_loa_m?: number | null; max_beam_m?: number | null; [key: string]: unknown; }
export interface Location { id: string; name: string; country_code?: string | null; unlocode?: string | null; function?: string | null; functions?: string | null; function_code?: string | null; latitude?: number | null; longitude?: number | null; source?: string | null; provenance?: string | null; [key: string]: unknown; }
export interface CargoRequirement { id: string; cargo_type?: string | null; material: string; quantity_mt: number; origin_location_id?: string | null; destination_location_id?: string | null; earliest_delivery?: string | null; latest_delivery?: string | null; priority: string; provenance: string; source?: string | null; source_reference?: string | null; status: string; created_at: string; updated_at: string; }
export interface Vessel { id: string; imo?: string | null; mmsi?: string | null; name: string; vessel_class?: string | null; ship_type?: string | null; flag?: string | null; dwt?: number | null; gt?: number | null; loa_m?: number | null; beam_m?: number | null; max_draft_m?: number | null; cargo_capacity_mt?: number | null; year_built?: number | null; source?: string | null; provenance: string; observed_at?: string | null; [key: string]: unknown; }
export interface MarketObservation { id: string; market_type: string; metric: string; value: number; unit: string; currency?: string | null; vessel_class?: string | null; observed_at: string; source: string; source_reference?: string | null; provenance: string; [key: string]: unknown; }
export interface FreightForecast { id: string; origin_location_id?: string | null; destination_location_id?: string | null; vessel_class?: string | null; p10: number; p50: number; p90: number; baseline: number; model_name?: string | null; model_version?: string | null; mae?: number | null; rmse?: number | null; smape?: number | null; interval_coverage?: number | null; confidence?: number | null; provenance: string; generated_at: string; [key: string]: unknown; }
export interface FeasibilityResponse { id: string; cargo_requirement_id: string; vessel_id: string; origin_port_id: string; destination_port_id: string; result: string; cargo_capacity_ok: boolean | null; cargo_compatibility_ok: boolean | null; origin_loa_ok: boolean | null; origin_beam_ok: boolean | null; origin_draft_ok: boolean | null; destination_loa_ok: boolean | null; destination_beam_ok: boolean | null; destination_draft_ok: boolean | null; loading_capability_ok: boolean | null; discharge_capability_ok: boolean | null; delivery_window_ok: boolean | null; reasons: string[]; checks: Record<string, unknown>; provenance: string; }

type ListEnvelope<T> = T[] | { count?: number; data?: T[] };

function unwrapList<T>(result: ListEnvelope<T>): T[] { return Array.isArray(result) ? result : Array.isArray(result.data) ? result.data : []; }

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { headers: { "Content-Type": "application/json", ...(options?.headers || {}) }, ...options });
  if (!response.ok) { const text = await response.text(); throw new Error(`API ${response.status}: ${text || response.statusText}`); }
  return response.json();
}

function normalizeCountryCode(value: unknown): string { const raw = String(value ?? "").trim().toUpperCase(); return /^[A-Z]{2}$/.test(raw) ? raw : ""; }
function countryCodeFromRecord(record: Record<string, unknown>): string {
  const direct = normalizeCountryCode(record.iso2 ?? record.iso_2 ?? record.country_code ?? record.countryCode ?? record.code ?? record.country);
  if (direct) return direct;
  const locode = String(record.unlocode ?? record.locode ?? record.location_code ?? record.locationCode ?? "").trim().toUpperCase();
  return /^[A-Z]{2}[A-Z0-9]{3}$/.test(locode) ? locode.slice(0, 2) : "";
}
function unlocodeFromRecord(record: Record<string, unknown>): string { return String(record.unlocode ?? record.locode ?? record.location_code ?? record.locationCode ?? record.code ?? "").trim().toUpperCase(); }
function displayCountryName(code: string): string { try { return new Intl.DisplayNames(["en"], { type: "region" }).of(code) || code; } catch { return code; } }
function countriesFromLocations(locations: Location[]): Country[] {
  const map = new Map<string, Country>();
  for (const location of locations) { const raw = location as unknown as Record<string, unknown>; const code = countryCodeFromRecord(raw); if (!code || map.has(code)) continue; map.set(code, { id: `derived-country-${code}`, name: displayCountryName(code), iso2: code, country_code: code, provenance: "DERIVED" }); }
  return [...map.values()].sort((a, b) => a.name.localeCompare(b.name));
}
let locationFallbackPromise: Promise<Location[]> | null = null;
async function listLocationsRaw(): Promise<Location[]> {
  if (!locationFallbackPromise) locationFallbackPromise = request<ListEnvelope<Location>>("/api/v1/locations").then(unwrapList).catch(() => []);
  return locationFallbackPromise;
}
function locationToPort(location: Location, countryCode?: string): Port | null {
  const raw = location as unknown as Record<string, unknown>; const unlocode = unlocodeFromRecord(raw); const code = countryCodeFromRecord(raw) || unlocode.slice(0, 2);
  if (!unlocode || !/^[A-Z]{2}[A-Z0-9]{3}$/.test(unlocode)) return null; if (countryCode && code !== countryCode) return null;
  const fn = String(location.function ?? location.functions ?? location.function_code ?? raw.function_code ?? raw.functions ?? "").replace(/\s+/g, "");
  if (fn && !fn.startsWith("1")) return null;
  return { id: location.id, name: location.name, location_id: location.id, unlocode, latitude: location.latitude ?? (typeof raw.lat === "number" ? raw.lat : null), longitude: location.longitude ?? (typeof raw.lon === "number" ? raw.lon : null), source: location.source ?? "UNECE UN/LOCODE", provenance: location.provenance ?? "PUBLIC_PROXY", ...raw } as Port;
}

export async function listCountries(): Promise<Country[]> {
  try { const primary = unwrapList(await request<ListEnvelope<Country>>("/api/v1/countries")); const usable = primary.filter(c => countryCodeFromRecord(c as unknown as Record<string, unknown>)); if (usable.length) return usable; } catch { /* deterministic reference data below */ }
  const derived = countriesFromLocations(await listLocationsRaw());
  return derived.length ? derived : REFERENCE_COUNTRIES;
}

export async function listLocations(): Promise<Location[]> { return listLocationsRaw(); }

export async function listPorts(countryCode?: string): Promise<Port[]> {
  const normalized = normalizeCountryCode(countryCode); const query = normalized ? `?country_code=${encodeURIComponent(normalized)}&limit=1000` : "?limit=1000";
  try { const primary = unwrapList(await request<ListEnvelope<Port>>(`/api/v1/ports${query}`)); const validPrimary = primary.filter(p => unlocodeFromRecord(p as unknown as Record<string, unknown>)); if (validPrimary.length) return validPrimary; } catch { /* deterministic reference data below */ }
  const locationPorts = (await listLocationsRaw()).map(location => locationToPort(location, normalized)).filter((port): port is Port => Boolean(port));
  if (locationPorts.length) return locationPorts;
  return REFERENCE_PORTS.filter(p => !normalized || p.unlocode?.slice(0, 2) === normalized);
}

export async function listCargo(): Promise<CargoRequirement[]> {
  try { const primary = unwrapList(await request<ListEnvelope<CargoRequirement>>("/api/v1/cargo?limit=500")); if (primary.length) return primary; } catch { /* deterministic reference data below */ }
  return REFERENCE_CARGO_ROWS;
}
export async function createCargo(payload: { cargo_type: string; material: string; quantity_mt: number; origin_location_id: string; destination_location_id: string; earliest_delivery: string; latest_delivery: string; priority: string; }): Promise<CargoRequirement> { return request<CargoRequirement>("/api/v1/cargo", { method: "POST", body: JSON.stringify({ ...payload, provenance: "USER_PROVIDED", source: "CHARTERPULSE_WEB", source_reference: "NEW_PROCUREMENT" }) }); }
export async function listVessels(): Promise<Vessel[]> { return unwrapList(await request<ListEnvelope<Vessel>>("/api/v1/vessels?limit=500")); }
export async function listMarketObservations(): Promise<MarketObservation[]> {
  try { const primary = unwrapList(await request<ListEnvelope<MarketObservation>>("/api/v1/market/observations?limit=500")); return primary.length ? [...primary, ...REFERENCE_MARKET_OBSERVATIONS] : REFERENCE_MARKET_OBSERVATIONS; } catch { return REFERENCE_MARKET_OBSERVATIONS; }
}
export async function listFreightForecasts(): Promise<FreightForecast[]> {
  try { const primary = unwrapList(await request<ListEnvelope<FreightForecast>>("/api/v1/forecasts/freight?limit=100")); return primary.length ? primary : [REFERENCE_FORECAST]; } catch { return [REFERENCE_FORECAST]; }
}
export async function evaluateFeasibility(payload: { cargo_requirement_id: string; vessel_id: string; origin_port_id: string; destination_port_id: string; }): Promise<FeasibilityResponse> { return request<FeasibilityResponse>("/api/v1/feasibility", { method: "POST", body: JSON.stringify(payload) }); }
export async function evaluateDecision(cargoQuantityMt: number, waitDays: number, cargoRequirementId: string = TEST_CARGO_ID, forecastId: string = TEST_FORECAST_ID): Promise<DecisionResponse> { return request<DecisionResponse>("/api/v1/decision/evaluate", { method: "POST", body: JSON.stringify({ forecast_id: forecastId, cargo_requirement_id: cargoRequirementId, cargo_quantity_mt: cargoQuantityMt, wait_days: waitDays, simulations: 5000, seed: 42, currency: "USD" }) }); }
export async function recordHumanDecision(decisionRunId: string, action: "APPROVE" | "MODIFY" | "REJECT", reason: string): Promise<HumanDecisionResponse> { return request<HumanDecisionResponse>("/api/v1/decisions/human", { method: "POST", body: JSON.stringify({ decision_run_id: decisionRunId, action, modified_parameters: {}, reason, actor_reference: "CHARTERPULSE_WEB_USER" }) }); }
