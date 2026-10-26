export type ForecastCandidate = {
  id: string;
  origin_location_id?: string | null;
  destination_location_id?: string | null;
  vessel_class?: string | null;
  p10: number;
  p50: number;
  p90: number;
  unit?: string | null;
  provenance?: string | null;
  generated_at?: string | null;
  metadata?: unknown;
};

export type ForecastRoute = {
  originLocationId?: string | null;
  destinationLocationId?: string | null;
  vesselClass?: string | null;
};

const ALLOWED_SOURCE_PROVENANCES = new Set(["REAL", "PUBLIC_PROXY"]);

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function finiteNumber(value: unknown): number | null {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }
  if (typeof value !== "string" || value.trim() === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function normalizeClass(value: string | null | undefined): string | null {
  const normalized = String(value ?? "").trim().toLocaleLowerCase();
  return normalized || null;
}

/**
 * A forecast is eligible for the decision engine only when it has explicit,
 * route-scoped provenance and quantiles derived from at least three distinct
 * dates of non-simulated, source-backed observations.
 *
 * Legacy PUBLIC_PROXY_REFERENCE rows and generic/demo forecasts intentionally
 * fail this check even when their route UUIDs happen to match.
 */
export function isEvidenceBackedForecast(value: unknown): value is ForecastCandidate {
  const record = asRecord(value);
  if (!record) return false;

  if (String(record.provenance ?? "").trim().toUpperCase() !== "FORECAST") {
    return false;
  }

  if (
    typeof record.origin_location_id !== "string" ||
    !record.origin_location_id.trim() ||
    typeof record.destination_location_id !== "string" ||
    !record.destination_location_id.trim() ||
    record.origin_location_id === record.destination_location_id
  ) {
    return false;
  }

  if (record.vessel_class !== null && record.vessel_class !== undefined &&
      typeof record.vessel_class !== "string") {
    return false;
  }

  if (String(record.unit ?? "").trim().toUpperCase().replace(/\s+/g, "") !== "USD/MT") {
    return false;
  }

  const p10 = finiteNumber(record.p10);
  const p50 = finiteNumber(record.p50);
  const p90 = finiteNumber(record.p90);
  if (p10 === null || p50 === null || p90 === null) return false;
  if (p10 < 0 || p50 <= 0 || p90 <= 0 || p10 > p50 || p50 > p90) {
    return false;
  }

  if (
    typeof record.generated_at !== "string" ||
    !Number.isFinite(Date.parse(record.generated_at))
  ) {
    return false;
  }

  const metadata = asRecord(record.metadata);
  if (!metadata) return false;
  if (metadata.route_scoped !== true) return false;
  if (String(metadata.input_provenance ?? "").trim().toUpperCase() !== "MARKET_OBSERVATION") {
    return false;
  }

  const observationCount = finiteNumber(metadata.observation_count);
  const distinctDates = finiteNumber(metadata.distinct_observation_dates);
  if (
    observationCount === null ||
    !Number.isInteger(observationCount) ||
    observationCount < 3 ||
    distinctDates === null ||
    !Number.isInteger(distinctDates) ||
    distinctDates < 3
  ) {
    return false;
  }

  const sourceLabels = metadata.source_labels;
  if (
    !Array.isArray(sourceLabels) ||
    sourceLabels.length === 0 ||
    !sourceLabels.every((label) => typeof label === "string" && label.trim().length > 0)
  ) {
    return false;
  }

  const sourceProvenances = metadata.source_provenances;
  if (!Array.isArray(sourceProvenances) || sourceProvenances.length === 0) {
    return false;
  }
  if (
    !sourceProvenances.every((source) =>
      typeof source === "string" &&
      ALLOWED_SOURCE_PROVENANCES.has(source.trim().toUpperCase())
    )
  ) {
    return false;
  }

  return true;
}

export function selectVerifiedRouteForecast<T extends ForecastCandidate>(
  forecasts: readonly T[],
  route: ForecastRoute,
): T | null {
  const originLocationId = route.originLocationId?.trim();
  const destinationLocationId = route.destinationLocationId?.trim();
  if (!originLocationId || !destinationLocationId || originLocationId === destinationLocationId) {
    return null;
  }

  const requestedClass = normalizeClass(route.vesselClass);
  return forecasts
    .filter(isEvidenceBackedForecast)
    .filter((forecast) =>
      forecast.origin_location_id === originLocationId &&
      forecast.destination_location_id === destinationLocationId &&
      normalizeClass(forecast.vessel_class) === requestedClass
    )
    .sort((left, right) =>
      Date.parse(right.generated_at || "") - Date.parse(left.generated_at || "")
    )[0] ?? null;
}
