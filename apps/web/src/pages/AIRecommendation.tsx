import { useEffect, useMemo, useState } from "react";
import {
  evaluateDecision,
  listFreightForecasts,
  listVessels,
  type DecisionResponse,
  type FreightForecast,
  type Vessel,
} from "../api";
import { selectVerifiedRouteForecast } from "../utils/forecastEligibility";
import type { ProcurementContext } from "./NewProcurement";

export default function AIRecommendation({
  procurement,
  decision,
  onDecision,
}: {
  procurement: ProcurementContext | null;
  decision: DecisionResponse | null;
  onDecision: (decision: DecisionResponse) => void;
}) {
  const [forecast, setForecast] = useState<FreightForecast | null>(null);
  const [vessels, setVessels] = useState<Vessel[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [forecastLoading, setForecastLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    listVessels()
      .then((rows) => {
        if (!cancelled) setVessels(rows);
      })
      .catch(() => {
        if (!cancelled) setVessels([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setForecast(null);
    setError("");

    if (
      !procurement?.cargo.origin_location_id ||
      !procurement.cargo.destination_location_id
    ) {
      setForecastLoading(false);
      return;
    }

    setForecastLoading(true);
    listFreightForecasts(
      procurement.cargo.origin_location_id,
      procurement.cargo.destination_location_id,
      procurement.vesselClass ?? undefined,
    )
      .then((rows) => {
        if (cancelled) return;
        const selected = selectVerifiedRouteForecast(rows, {
          originLocationId: procurement.cargo.origin_location_id,
          destinationLocationId: procurement.cargo.destination_location_id,
          vesselClass: procurement.vesselClass,
        });
        setForecast(selected);
        if (!selected) {
          setError(
            "No evidence-backed forecast matches this exact route and vessel class. Simulated and generic reference forecasts are not substituted.",
          );
        }
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        setForecast(null);
        setError(
          cause instanceof Error
            ? cause.message
            : "Unable to load the route-specific forecast.",
        );
      })
      .finally(() => {
        if (!cancelled) setForecastLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [procurement]);

  const recommendedVessel = useMemo(
    () =>
      vessels
        .filter((vessel) =>
          (vessel.cargo_capacity_mt || vessel.dwt || 0) >=
          (procurement?.cargo.quantity_mt || 0),
        )
        .sort(
          (left, right) =>
            (left.cargo_capacity_mt || left.dwt || 0) -
            (right.cargo_capacity_mt || right.dwt || 0),
        )[0] ||
      vessels.find((vessel) =>
        String(vessel.vessel_class).toLowerCase().includes("panamax"),
      ),
    [vessels, procurement],
  );

  async function run() {
    if (!procurement || !forecast || busy) return;
    setBusy(true);
    setError("");
    try {
      onDecision(
        await evaluateDecision(
          procurement.cargo.quantity_mt,
          7,
          procurement.cargo.id,
          forecast.id,
        ),
      );
    } catch (cause: unknown) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Decision engine unavailable.",
      );
    } finally {
      setBusy(false);
    }
  }

  const savings = decision?.wait_cost_difference ?? 0;
  const strategy =
    decision?.recommendation === "CHARTER_NOW"
      ? "Spot / short-period charter · immediate fixture review"
      : decision?.recommendation === "WAIT"
        ? "Delay commitment · retain optionality and re-price before laycan"
        : "Commercial review required before commitment";

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <span className="eyebrow">DECISION / AI RECOMMENDATION</span>
          <h1>AI Recommendation</h1>
          <p>
            Recommendations require a verified forecast for the active
            procurement's exact route and vessel class. Static references and
            simulated forecasts cannot drive a decision.
          </p>
        </div>
        {decision && (
          <span className={"data-badge " + (
            decision.provenance === "REAL"
              ? "real"
              : decision.provenance === "PUBLIC_PROXY"
                ? "proxy"
                : "simulated"
          )}>
            {decision.provenance}
          </span>
        )}
      </div>

      {procurement ? (
        <section className="enterprise-card decision-hero">
          <div>
            <span className="eyebrow">ACTIVE REQUIREMENT</span>
            <h2>
              {decision
                ? decision.recommendation === "CHARTER_NOW"
                  ? "CHART NOW"
                  : decision.recommendation.replace(/_/g, " ")
                : "AWAITING VERIFIED FORECAST"}
            </h2>
            <p>
              {procurement.cargo.material} · {procurement.cargo.quantity_mt.toLocaleString()} MT · {procurement.originPort.name} → {procurement.destinationPort.name}
            </p>
            <p>
              {decision?.rationale?.[0] ||
                (forecastLoading
                  ? "Checking for matching source-backed route observations…"
                  : error || "A decision will be available when matching verified market observations exist.")}
            </p>
          </div>
          <button className="primary-button" onClick={run} disabled={busy || forecastLoading || !forecast}>
            {busy ? "OPTIMIZING…" : forecastLoading ? "CHECKING DATA…" : "RUN OPTIMIZATION"}
          </button>
        </section>
      ) : (
        <section className="enterprise-card">
          <h2>No active procurement</h2>
          <p>Create a requirement first so the recommendation is tied to a cargo record.</p>
        </section>
      )}

      {error && <div className="error-banner" role="alert">{error}</div>}

      {decision && (
        <>
          <div className="metric-grid four">
            <div className="metric-card">
              <span>CHARTER DECISION</span>
              <strong>{decision.recommendation === "CHARTER_NOW" ? "CHART NOW" : decision.recommendation.replace(/_/g, " ")}</strong>
              <small>Timing recommendation</small>
            </div>
            <div className="metric-card">
              <span>VESSEL</span>
              <strong>{recommendedVessel?.vessel_class || recommendedVessel?.name || "REVIEW"}</strong>
              <small>{recommendedVessel?.name || "No vessel record"} · {recommendedVessel?.cargo_capacity_mt?.toLocaleString() || recommendedVessel?.dwt?.toLocaleString() || "—"} MT</small>
            </div>
            <div className="metric-card">
              <span>EXPECTED SAVINGS</span>
              <strong>${Math.max(0, savings).toLocaleString(undefined, { maximumFractionDigits: 0 })}</strong>
              <small>vs conservative wait case</small>
            </div>
            <div className="metric-card">
              <span>RISK SCORE</span>
              <strong>{decision.risk_score.toFixed(1)}</strong>
              <small>0–100 decision risk</small>
            </div>
          </div>

          <section className="enterprise-card">
            <div className="recommendation-grid">
              <div>
                <span className="eyebrow">CONTRACT STRATEGY</span>
                <h3>{strategy}</h3>
                <p>Contracting remains a human commercial decision.</p>
              </div>
              <div>
                <span className="eyebrow">WHY THIS DECISION</span>
                <ul>{decision.rationale.map((item, index) => <li key={index}>{item}</li>)}</ul>
              </div>
              <div>
                <span className="eyebrow">DATA WARNINGS</span>
                <ul>{decision.warnings.length ? decision.warnings.map((item, index) => <li key={index}>{item}</li>) : <li>No additional warnings returned.</li>}</ul>
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
