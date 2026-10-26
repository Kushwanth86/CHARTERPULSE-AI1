import { useEffect, useMemo, useState } from "react";
import { listFreightForecasts, listPorts, type FreightForecast, type Port } from "../api";
import { selectVerifiedRouteForecast } from "../utils/forecastEligibility";
import { isUuid, isValidUnlocode } from "../utils/procurementValidation";

const radians = (value: number) => value * Math.PI / 180;
function nauticalMiles(origin: Port, destination: Port): number | null {
  if (origin.latitude == null || origin.longitude == null || destination.latitude == null || destination.longitude == null) return null;
  const dLat = radians(destination.latitude - origin.latitude);
  const dLon = radians(destination.longitude - origin.longitude);
  const a = Math.sin(dLat / 2) ** 2 +
    Math.cos(radians(origin.latitude)) * Math.cos(radians(destination.latitude)) * Math.sin(dLon / 2) ** 2;
  return 3440.065 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(Math.max(0, 1 - a)));
}
const money = (value: number | null) => value == null || !Number.isFinite(value)
  ? "—"
  : "$" + value.toLocaleString("en-US", { maximumFractionDigits: 2 });

function sourceLabel(forecast: FreightForecast | null): string {
  if (!forecast) return "NO VERIFIED FORECAST";
  const metadata = typeof forecast.metadata === "object" && forecast.metadata !== null
    ? forecast.metadata as Record<string, unknown> : {};
  const sources = Array.isArray(metadata.source_provenances)
    ? metadata.source_provenances.map((source) => String(source).trim().toUpperCase()) : [];
  if (sources.length === 1 && sources[0] === "REAL") return "REAL SOURCE OBSERVATIONS";
  if (sources.length === 1 && sources[0] === "PUBLIC_PROXY") return "PUBLIC PROXY · INDICATIVE";
  return "MIXED SOURCE OBSERVATIONS";
}

export default function CostCharting() {
  const [ports, setPorts] = useState<Port[]>([]);
  const [originId, setOriginId] = useState("");
  const [destinationId, setDestinationId] = useState("");
  const [vesselClass, setVesselClass] = useState("");
  const [quantityInput, setQuantityInput] = useState("");
  const [forecast, setForecast] = useState<FreightForecast | null>(null);
  const [portsError, setPortsError] = useState("");
  const [forecastError, setForecastError] = useState("");
  const [loadingForecast, setLoadingForecast] = useState(false);

  useEffect(() => {
    let cancelled = false;
    listPorts().then((rows) => {
      if (cancelled) return;
      const usable = rows.filter(
        (port) => isUuid(port.location_id) && isValidUnlocode(port.unlocode),
      );
      setPorts(usable);
      setPortsError(usable.length ? "" : "No verified port records were returned by the API.");
    }).catch((cause: unknown) => {
      if (cancelled) return;
      setPorts([]);
      setPortsError(cause instanceof Error ? cause.message : "Unable to load ports.");
    });
    return () => { cancelled = true; };
  }, []);

  const origin = ports.find((port) => port.id === originId);
  const destination = ports.find((port) => port.id === destinationId);
  const distance = origin && destination ? nauticalMiles(origin, destination) : null;
  const parsedQuantity = quantityInput.trim() === "" ? null : Number(quantityInput);
  const quantityValid = parsedQuantity !== null && Number.isFinite(parsedQuantity) && parsedQuantity > 0;

  useEffect(() => {
    let cancelled = false;
    setForecast(null);
    setForecastError("");
    if (!origin?.location_id || !destination?.location_id ||
        origin.location_id === destination.location_id || !vesselClass) {
      setLoadingForecast(false);
      return;
    }
    setLoadingForecast(true);
    listFreightForecasts(origin.location_id, destination.location_id, vesselClass)
      .then((rows) => {
        if (cancelled) return;
        const matched = selectVerifiedRouteForecast(rows, {
          originLocationId: origin.location_id,
          destinationLocationId: destination.location_id,
          vesselClass,
        });
        setForecast(matched);
        if (!matched) setForecastError(
          "No evidence-backed forecast matches this exact route and vessel class. Static reference prices are not substituted.",
        );
      }).catch((cause: unknown) => {
        if (cancelled) return;
        setForecast(null);
        setForecastError(cause instanceof Error ? cause.message : "Unable to load the route forecast.");
      }).finally(() => {
        if (!cancelled) setLoadingForecast(false);
      });
    return () => { cancelled = true; };
  }, [origin?.location_id, destination?.location_id, vesselClass]);

  const freightRate = forecast ? forecast.p50 : null;
  const freightOnlyEstimate = freightRate !== null && quantityValid
    ? freightRate * (parsedQuantity as number) : null;
  const routeStatus = useMemo(() => {
    if (!origin || !destination) return "Select both ports to inspect the route.";
    if (origin.location_id === destination.location_id) return "Origin and destination must differ.";
    if (distance === null) return "Coordinates are unavailable for one or both ports.";
    return distance.toLocaleString("en-US", { maximumFractionDigits: 0 }) + " nautical miles (great-circle distance).";
  }, [origin, destination, distance]);

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div><span className="eyebrow">DECISION / COST ENGINE</span><h1>Cost & Chartering</h1>
          <p>The page shows a freight-only estimate only when a verified route/class forecast exists. It does not fabricate a landed-cost total from fixed port, canal, bunker, or demurrage assumptions.</p>
        </div>
        <span className="data-badge proxy">{sourceLabel(forecast)}</span>
      </div>

      <section className="enterprise-card">
        <div className="section-head">
          <div><span className="eyebrow">ROUTE INPUTS</span><h2>Cost context</h2></div>
          <span className="field-note">No preselected route or quantity</span>
        </div>
        <div className="form-grid four">
          <div className="field"><label>ORIGIN PORT</label>
            <select value={originId} onChange={(event) => setOriginId(event.target.value)}>
              <option value="">Select origin</option>
              {ports.map((port) => <option key={port.id} value={port.id}>{port.name} · {port.unlocode}</option>)}
            </select>
          </div>
          <div className="field"><label>DESTINATION PORT</label>
            <select value={destinationId} onChange={(event) => setDestinationId(event.target.value)}>
              <option value="">Select destination</option>
              {ports.map((port) => <option key={port.id} value={port.id}>{port.name} · {port.unlocode}</option>)}
            </select>
          </div>
          <div className="field"><label>VESSEL CLASS</label>
            <select value={vesselClass} onChange={(event) => setVesselClass(event.target.value)}>
              <option value="">Select vessel class</option><option value="Handysize">Handysize</option>
              <option value="Panamax">Panamax</option><option value="Capesize">Capesize</option>
            </select>
          </div>
          <div className="field"><label>CARGO QUANTITY (MT)</label>
            <div className="input-unit"><input type="number" min="0" step="any" value={quantityInput}
              onChange={(event) => setQuantityInput(event.target.value)} placeholder="Enter quantity" /><span>MT</span></div>
            <small>Finite positive quantity required.</small>
          </div>
        </div>
        {portsError && <div className="error-banner" role="alert">{portsError}</div>}
      </section>

      <div className="waterfall-grid">
        <section className="enterprise-card">
          <div className="section-head compact">
            <div><span className="eyebrow">FREIGHT-ONLY ESTIMATE</span><h2>Source-backed route rate</h2></div>
            <span className="field-note">No synthetic fallback</span>
          </div>
          <div className="cost-row">
            <div><strong>Great-circle route distance</strong><small>{routeStatus}</small></div>
            <div className="cost-row-value"><strong>{distance == null ? "—" : distance.toLocaleString("en-US", { maximumFractionDigits: 0 }) + " nm"}</strong></div>
          </div>
          <div className="cost-row">
            <div><strong>Route-matched forecast P50</strong>
              <small>{forecast ? (forecast.model_name || "Forecast model") + " · " + forecast.generated_at.slice(0, 10) + " · " + forecast.unit :
                loadingForecast ? "Checking source-backed observations…" : forecastError || "Choose ports and vessel class."}</small>
            </div>
            <div className="cost-row-value"><strong>{money(freightRate)}</strong><span className="cost-status">{forecast ? forecast.unit : "UNAVAILABLE"}</span></div>
          </div>
          <div className="cost-row">
            <div><strong>Freight-only amount</strong>
              <small>{quantityValid ? (parsedQuantity as number).toLocaleString() + " MT × verified P50 rate" : "Enter a finite positive cargo quantity."}</small>
            </div>
            <div className="cost-row-value"><strong>{money(freightOnlyEstimate)}</strong><span className="cost-status">{freightOnlyEstimate === null ? "NOT CALCULATED" : "FREIGHT ONLY"}</span></div>
          </div>
          {forecastError && <div className="error-banner" role="alert">{forecastError}</div>}
          <div className="source-strip"><span>WHAT IS NOT INCLUDED</span>
            <strong>Bunker, port/canal charges, loading/discharge, demurrage, storage, inland logistics and insurance are unavailable from verified inputs and are excluded.</strong>
          </div>
        </section>

        <section className="enterprise-card cost-context">
          <span className="eyebrow">DATA READINESS</span><h2>{forecast ? "Route forecast matched" : "Route forecast unavailable"}</h2>
          <p>{forecast
            ? "The displayed rate is a source-backed USD/MT forecast for the selected route and vessel class. Public proxy source values remain indicative, not carrier quotes."
            : "No freight price is displayed until the API returns a forecast with matched route, vessel class, unit, provenance and adequate historical evidence."}</p>
          <div className="route-fact"><span>FORECAST SOURCE</span><strong>{sourceLabel(forecast)}</strong></div>
          <div className="route-fact"><span>MODEL CONFIDENCE</span><strong>{forecast?.confidence == null ? "—" : (forecast.confidence * 100).toFixed(1) + "%"}</strong></div>
          <span className="data-badge proxy">PARTIAL COST ONLY</span>
        </section>
      </div>
    </div>
  );
}
