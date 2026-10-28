import { useEffect, useMemo, useState } from "react";
import {
  listFreightForecasts,
  listMarketObservations,
  type FreightForecast,
  type MarketObservation,
} from "../api";
import { isEvidenceBackedForecast } from "../utils/forecastEligibility";

function LineChart({ history }: { history: MarketObservation[] }) {
  const points = history
    .filter((row) => Number.isFinite(row.value) && row.value > 0 && Number.isFinite(Date.parse(row.observed_at)))
    .sort((left, right) => left.observed_at.localeCompare(right.observed_at))
    .map((row) => ({
      label: row.observed_at.slice(5, 10),
      value: row.value,
    }));

  if (!points.length) {
    return (
      <div className="chart-shell">
        <p className="field-note">
          No route-matched, non-simulated historical observations are available
          for this forecast. The chart will not invent interpolated history or
          weekly future points.
        </p>
      </div>
    );
  }

  const values = points.map((point) => point.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const width = 900;
  const height = 300;
  const x = (index: number) =>
    40 + index * ((width - 70) / Math.max(1, points.length - 1));
  const y = (value: number) =>
    height - 30 - ((value - min) / Math.max(0.0001, max - min)) * (height - 55);
  const path = points
    .map((point, index) => (index ? "L" : "M") + x(index) + "," + y(point.value))
    .join(" ");

  return (
    <div className="chart-shell">
      <svg viewBox={"0 0 " + width + " " + height} className="forecast-svg" role="img" aria-label="Observed route-specific freight rates">
        <line x1="40" x2="870" y1={height - 30} y2={height - 30} className="chart-axis" />
        <path d={path} className="chart-line median" />
        {points.map((point, index) => (
          <g key={point.label + "-" + index}>
            <circle cx={x(index)} cy={y(point.value)} r="3.5" className="chart-point" />
            <text x={x(index)} y={height - 8} className="chart-label" textAnchor="middle">{point.label}</text>
          </g>
        ))}
      </svg>
      <div className="chart-legend">
        <span><i className="legend-median" />Observed rates only</span>
        <span>USD/MT</span>
      </div>
    </div>
  );
}

function evidenceMetadata(forecast: FreightForecast): Record<string, unknown> {
  return typeof forecast.metadata === "object" && forecast.metadata !== null
    ? forecast.metadata as Record<string, unknown>
    : {};
}

export default function FreightForecast() {
  const [forecasts, setForecasts] = useState<FreightForecast[]>([]);
  const [observations, setObservations] = useState<MarketObservation[]>([]);
  const [selected, setSelected] = useState<FreightForecast | null>(null);
  const [excludedForecastCount, setExcludedForecastCount] = useState(0);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      listFreightForecasts(),
      listMarketObservations(),
    ])
      .then(([allForecasts, marketRows]) => {
        if (cancelled) return;
        const evidenceBacked = allForecasts.filter(isEvidenceBackedForecast);
        setForecasts(evidenceBacked);
        setExcludedForecastCount(allForecasts.length - evidenceBacked.length);
        setObservations(marketRows);
        setSelected(evidenceBacked[0] || null);
        setLoadError("");
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        setForecasts([]);
        setObservations([]);
        setSelected(null);
        setLoadError(
          cause instanceof Error
            ? cause.message
            : "Unable to load forecasts and source observations.",
        );
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const freightHistory = useMemo(() => {
    if (!selected) return [];
    const selectedClass = String(selected.vessel_class ?? "").trim().toLocaleLowerCase();
    return observations.filter((row) => {
      const source = String(row.provenance ?? "").trim().toUpperCase();
      return (
        (source === "REAL" || source === "PUBLIC_PROXY") &&
        String(row.origin_location_id ?? "") === String(selected.origin_location_id ?? "") &&
        String(row.destination_location_id ?? "") === String(selected.destination_location_id ?? "") &&
        String(row.vessel_class ?? "").trim().toLocaleLowerCase() === selectedClass &&
        String(row.metric ?? "").toLowerCase().includes("freight") &&
        row.unit === selected.unit &&
        Number.isFinite(row.value) &&
        row.value > 0
      );
    }).sort((left, right) => left.observed_at.localeCompare(right.observed_at));
  }, [observations, selected]);

  const metadata = selected ? evidenceMetadata(selected) : {};
  const sourceProvenances = Array.isArray(metadata.source_provenances)
    ? metadata.source_provenances.map((value) => String(value).toUpperCase())
    : [];
  const sourceLabel = sourceProvenances.includes("REAL")
    ? (sourceProvenances.includes("PUBLIC_PROXY") ? "MIXED SOURCE OBSERVATIONS" : "REAL OBSERVATIONS")
    : "PUBLIC PROXY OBSERVATIONS";

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <span className="eyebrow">MARKET INTELLIGENCE / FORECAST</span>
          <h1>Freight Forecast</h1>
          <p>
            Only route-scoped forecasts backed by source-attributed observations
            from at least three distinct dates are shown. Charts display recorded
            observations only; no synthetic future curve is drawn.
          </p>
        </div>
        {selected && <span className={"data-badge " + (sourceProvenances.includes("REAL") ? "real" : "proxy")}>{sourceLabel}</span>}
      </div>

      {loadError && <div className="error-banner" role="alert">Forecast API unavailable: {loadError}</div>}

      {selected ? (
        <>
          <div className="metric-grid four">
            <div className="metric-card"><span>P10</span><strong>{selected.p10.toFixed(2)}</strong><small>Lower scenario · {selected.unit}</small></div>
            <div className="metric-card"><span>P50</span><strong>{selected.p50.toFixed(2)}</strong><small>Median · {selected.unit}</small></div>
            <div className="metric-card"><span>P90</span><strong>{selected.p90.toFixed(2)}</strong><small>Upper scenario · {selected.unit}</small></div>
            <div className="metric-card"><span>MODEL CONFIDENCE</span><strong>{selected.confidence == null ? "—" : (selected.confidence * 100).toFixed(1) + "%"}</strong><small>{selected.model_name || "Forecast model"}</small></div>
          </div>

          <section className="enterprise-card">
            <div className="section-head">
              <div><span className="eyebrow">EVIDENCE-BACKED FORECAST</span><h2>Route-specific forecast record</h2></div>
              <select value={selected.id} onChange={(event) => setSelected(forecasts.find((forecast) => forecast.id === event.target.value) || selected)}>
                {forecasts.map((forecast) => (
                  <option key={forecast.id} value={forecast.id}>
                    {(forecast.model_name || forecast.id) + " · " + forecast.generated_at.slice(0, 10)}
                  </option>
                ))}
              </select>
            </div>
            <p className="field-note">
              {String(selected.origin_location_id)} → {String(selected.destination_location_id)} · vessel class {selected.vessel_class || "unspecified"} · {Number(metadata.observation_count)} source observations across {Number(metadata.distinct_observation_dates)} dates.
            </p>
            <LineChart history={freightHistory} />
            <div className="forecast-meta">
              <span>MAE <strong>{selected.mae?.toFixed(2) ?? "—"}</strong></span>
              <span>RMSE <strong>{selected.rmse?.toFixed(2) ?? "—"}</strong></span>
              <span>sMAPE <strong>{selected.smape?.toFixed(2) ?? "—"}%</strong></span>
              <span>Coverage <strong>{selected.interval_coverage == null ? "Pending OOS test" : (selected.interval_coverage * 100).toFixed(1) + "%"}</strong></span>
            </div>
          </section>
        </>
      ) : (
        <section className="enterprise-card">
          <h2>No evidence-backed route forecast available</h2>
          <p>
            {excludedForecastCount
              ? excludedForecastCount + " stored forecast records were excluded because they lack verified route-specific evidence, source provenance, matching units, or enough distinct observation dates. "
              : ""}
            The current database does not yet contain a valid non-simulated market-observation series for this view. Static/demo reference values are intentionally not substituted for a live freight forecast.
          </p>
          <p>
            The present decision model supports USD/MT rates only. Container benchmarks in USD per 40-foot container and tanker Worldscale/TCE measures require their own correctly normalized market models before they can be used in this decision calculation.
          </p>
        </section>
      )}
    </div>
  );
}
