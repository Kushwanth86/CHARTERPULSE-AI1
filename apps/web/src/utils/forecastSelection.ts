import type { FreightForecast } from "../api";

export function selectRouteForecast(
  forecasts: FreightForecast[],
  originLocationId?: string | null,
  destinationLocationId?: string | null,
  vesselClass?: string | null,
): FreightForecast | null {
  if (!originLocationId || !destinationLocationId) return null;

  return (
    forecasts
      .filter(
        (forecast) =>
          forecast.origin_location_id === originLocationId &&
          forecast.destination_location_id === destinationLocationId &&
          (!vesselClass ||
            String(forecast.vessel_class ?? "")
              .trim()
              .toLowerCase() === vesselClass.trim().toLowerCase()),
      )
      .sort(
        (a, b) =>
          new Date(b.generated_at).getTime() -
          new Date(a.generated_at).getTime(),
      )[0] ?? null
  );
}
