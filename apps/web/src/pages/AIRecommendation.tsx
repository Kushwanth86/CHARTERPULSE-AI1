import { useEffect, useMemo, useState } from "react";
import { evaluateDecision, listFreightForecasts, listVessels, type DecisionResponse, type FreightForecast, type Vessel } from "../api";
import type { ProcurementContext } from "./NewProcurement";
import { selectRecommendedVessel, vesselCapacityMt } from "../utils/vesselSelection";
import { selectRouteForecast } from "../utils/forecastSelection";

export default function AIRecommendation({ procurement, decision, onDecision }: { procurement: ProcurementContext | null; decision: DecisionResponse | null; onDecision: (d: DecisionResponse) => void }) {
  const [forecasts, setForecasts] = useState<FreightForecast[]>([]); const [vessels, setVessels] = useState<Vessel[]>([]); const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    const originId = procurement?.cargo.origin_location_id ?? undefined;
    const destinationId = procurement?.cargo.destination_location_id ?? undefined;

    if (!originId || !destinationId) {
      setForecasts([]);
      setVessels([]);
      setError("");
      return () => {
        active = false;
      };
    }

    setError("");
    Promise.all([
      listFreightForecasts(
        originId,
        destinationId,
        procurement?.vesselClass ?? undefined,
      ),
      listVessels(),
    ])
      .then(([forecastRows, vesselRows]) => {
        if (!active) return;
        setForecasts(forecastRows);
        setVessels(vesselRows);
      })
      .catch((cause: unknown) => {
        if (!active) return;
        setForecasts([]);
        setVessels([]);
        setError(
          cause instanceof Error
            ? `Unable to load route forecast or vessel data: ${cause.message}`
            : "Unable to load route forecast or vessel data.",
        );
      });

    return () => {
      active = false;
    };
  }, [
    procurement?.cargo.origin_location_id,
    procurement?.cargo.destination_location_id,
    procurement?.vesselClass,
  ]);
  const forecast = useMemo(
    () =>
      selectRouteForecast(
        forecasts,
        procurement?.cargo.origin_location_id,
        procurement?.cargo.destination_location_id,
        procurement?.vesselClass,
      ),
    [
      forecasts,
      procurement?.cargo.origin_location_id,
      procurement?.cargo.destination_location_id,
      procurement?.vesselClass,
    ],
  );
  const recommendedVessel = useMemo(
    () =>
      selectRecommendedVessel(
        vessels,
        procurement?.cargo.quantity_mt ?? 0,
      ),
    [vessels, procurement?.cargo.quantity_mt],
  );
  async function run() { if (!procurement || !forecast) return; setBusy(true); setError(""); try { onDecision(await evaluateDecision(procurement.cargo.quantity_mt, 7, procurement.cargo.id, forecast.id)); } catch (e) { setError(e instanceof Error ? e.message : "Decision engine unavailable."); } finally { setBusy(false); } }
  const savings = decision?.wait_cost_difference ?? 0; const strategy = decision?.recommendation === "CHARTER_NOW" ? "Spot / short-period charter · immediate fixture review" : decision?.recommendation === "WAIT" ? "Delay commitment · retain optionality and re-price before laycan" : "Commercial review required before commitment";
  return <div className="page-stack"><div className="page-heading"><div><span className="eyebrow">DECISION / AI RECOMMENDATION</span><h1>AI Recommendation</h1><p>Recommendation state is driven by the active procurement, the selected forecast record and the existing decision response. No API contract is changed.</p></div>{decision && <span className={`data-badge ${decision.provenance === "SIMULATED" ? "simulated" : "proxy"}`}>{decision.provenance}</span>}</div>
    {procurement ? <section className="enterprise-card decision-hero"><div><span className="eyebrow">ACTIVE REQUIREMENT</span><h2>{decision ? (decision.recommendation === "CHARTER_NOW" ? "CHART NOW" : decision.recommendation.replace(/_/g, " ")) : "READY TO EVALUATE"}</h2><p>{procurement.cargo.material} · {procurement.cargo.quantity_mt.toLocaleString()} MT · {procurement.originPort.name} → {procurement.destinationPort.name}</p><p>{decision?.rationale?.[0] || (forecast ? "Run the decision engine to evaluate charter timing against the forecast distribution." : "No verified freight forecast is available for this route and vessel class. Matching verified market observations are required; unrelated route forecasts are not substituted.")}</p></div><button className="primary-button" onClick={run} disabled={busy || !forecast}>{busy ? "OPTIMIZING…" : "RUN OPTIMIZATION"}</button></section> : <section className="enterprise-card"><h2>No active procurement</h2><p>Create a requirement first so the recommendation is tied to a cargo record.</p></section>}
    {decision && <><div className="metric-grid four"><div className="metric-card"><span>CHARTER DECISION</span><strong>{decision.recommendation === "CHARTER_NOW" ? "CHART NOW" : decision.recommendation.replace(/_/g, " ")}</strong><small>Timing recommendation</small></div><div className="metric-card"><span>VESSEL</span><strong>{recommendedVessel?.vessel_class || recommendedVessel?.name || "REVIEW"}</strong><small>{recommendedVessel?.name || "No vessel record"} · {recommendedVessel ? vesselCapacityMt(recommendedVessel).toLocaleString() : "—"} MT</small></div><div className="metric-card"><span>EXPECTED SAVINGS</span><strong>${Math.max(0, savings).toLocaleString(undefined, { maximumFractionDigits: 0 })}</strong><small>vs conservative wait case</small></div><div className="metric-card"><span>RISK SCORE</span><strong>{decision.risk_score.toFixed(1)}</strong><small>0–100 decision risk</small></div></div><section className="enterprise-card"><div className="recommendation-grid"><div><span className="eyebrow">CONTRACT STRATEGY</span><h3>{strategy}</h3><p>Contracting remains a human commercial decision.</p></div><div><span className="eyebrow">WHY THIS DECISION</span><ul>{decision.rationale.map((r, i) => <li key={i}>{r}</li>)}</ul></div><div><span className="eyebrow">DATA WARNINGS</span><ul>{decision.warnings.length ? decision.warnings.map((r, i) => <li key={i}>{r}</li>) : <li>No additional warnings returned.</li>}</ul></div></div></section></>}{error && <div className="error-banner">{error}</div>}
  </div>;
}
