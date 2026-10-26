import { useEffect, useState } from "react";
import Sidebar from "./components/layout/Sidebar";
import { evaluateDecision, listFreightForecasts, recordHumanDecision, type DecisionResponse, type FreightForecast as FreightForecastData, type HumanDecisionResponse } from "./api";
import type { ProcurementContext } from "./pages/NewProcurement";
import { selectVerifiedRouteForecast } from "./utils/forecastEligibility";
import NewProcurement from "./pages/NewProcurement";
import MarketIntelligence from "./pages/MarketIntelligence";
import FreightForecast from "./pages/FreightForecast";
import ContainerFreight from "./pages/ContainerFreight";
import PortIntelligence from "./pages/PortIntelligence";
import VesselDirectory from "./pages/VesselDirectory";
import CostCharting from "./pages/CostCharting";
import WhatIfRisk from "./pages/WhatIfRisk";
import AIRecommendation from "./pages/AIRecommendation";
import DecisionHistory from "./pages/DecisionHistory";
import ActualOutcomes from "./pages/ActualOutcomes";
import ModelPerformance from "./pages/ModelPerformance";

type AuditEvent = { time: string; type: string; ref: string; detail: string; procurementId?: string };function formatDateOnly(value?: string | null): string {
  if (!value) return "—";
  const date = value.slice(0, 10);
  const [year, month, day] = date.split("-").map(Number);
  if (!year || !month || !day) return "—";
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(Date.UTC(year, month - 1, day)));
}

const AUDIT_KEY = "charterpulse.frontend.audit.v1";
function readAudit(): AuditEvent[] { try { return JSON.parse(localStorage.getItem(AUDIT_KEY) || "[]") as AuditEvent[]; } catch { return []; } }
function writeAudit(event: AuditEvent) { try { localStorage.setItem(AUDIT_KEY, JSON.stringify([event, ...readAudit()].slice(0, 50))); } catch { /* optional browser storage */ } }

function CommandCenter({ procurement, decision, decisionError, onDecision, human, onHuman, navigate }: { procurement: ProcurementContext | null; decision: DecisionResponse | null; decisionError: string; onDecision: (d: DecisionResponse) => void; human: HumanDecisionResponse | null; onHuman: (d: HumanDecisionResponse) => void; navigate: (id: string) => void }) {
  const [waitDays, setWaitDays] = useState(7);
  const [busy, setBusy] = useState(false);
  const [submittingAction, setSubmittingAction] = useState<"APPROVE" | "MODIFY" | "REJECT" | null>(null);
  const [error, setError] = useState("");
  const [actionMessage, setActionMessage] = useState("");

  async function run() {
    if (!procurement || busy || submittingAction) return;
    setBusy(true); setError(""); setActionMessage("");
    try {
      const forecasts = await listFreightForecasts(procurement.cargo.origin_location_id ?? undefined, procurement.cargo.destination_location_id ?? undefined, procurement.vesselClass ?? undefined);
      const selectedForecast = selectVerifiedRouteForecast(forecasts, {
        originLocationId: procurement.cargo.origin_location_id,
        destinationLocationId: procurement.cargo.destination_location_id,
        vesselClass: procurement.vesselClass,
      });
      if (!selectedForecast) throw new Error("No verified freight forecast is available for this route and vessel class. Matching verified market observations are required; generic and simulated forecasts are not substituted.");
      onDecision(await evaluateDecision(procurement.cargo.quantity_mt, waitDays, procurement.cargo.id, selectedForecast.id));
    } catch (e) { setError(e instanceof Error ? e.message : "Decision engine unavailable."); }
    finally { setBusy(false); }
  }

  async function act(action: "APPROVE" | "MODIFY" | "REJECT") {
    if (!decision?.decision_run_id || busy || submittingAction) return;
    setSubmittingAction(action); setError(""); setActionMessage("");
    try {
      const modifiedParameters = action === "MODIFY" ? { wait_days: waitDays } : {};
      const saved = await recordHumanDecision(decision.decision_run_id, action, `${action} from CharterPulse Command Center.`, modifiedParameters);
      onHuman(saved);
      setActionMessage(`Decision ${saved.action.toLowerCase()} was saved successfully.`);
    } catch (e) { setError(e instanceof Error ? e.message : "Unable to record human decision. The save was not confirmed."); }
    finally { setSubmittingAction(null); }
  }

  if (!procurement) return <div className="page-stack"><div className="page-heading"><div><span className="eyebrow">COMMAND CENTER</span><h1>Decision Room</h1><p>Create a procurement requirement first. The decision room never fills missing data with invented values.</p></div></div><section className="hero-command"><div><span className="eyebrow">FROM CARGO REQUIREMENT → BEST TRANSPORTATION DECISION</span><h2>Start the procurement intelligence workflow.</h2><p>Material → country → port → delivery window → forecast → vessel → cost → risk → human approval.</p></div><button className="primary-button" onClick={() => navigate("New Procurement")}>NEW PROCUREMENT</button></section></div>;
  return <div className="page-stack"><div className="page-heading"><div><span className="eyebrow">COMMAND CENTER / DECISION ROOM</span><h1>{procurement.cargo.material} procurement</h1><p>{procurement.cargo.quantity_mt.toLocaleString()} MT · {procurement.originPort.name} → {procurement.destinationPort.name}</p></div><span className={`data-badge ${decision?.provenance === "REAL" ? "real" : decision?.provenance === "PUBLIC_PROXY" || decision?.provenance === "MIXED_SOURCE" ? "proxy" : decision ? "simulated" : "unknown"}`}>{decision?.provenance || (decisionError ? "DATA REQUIRED" : "NOT RUN")}</span></div><div className="metric-grid four"><div className="metric-card"><span>DELIVERY WINDOW</span><strong>{formatDateOnly(procurement.cargo.earliest_delivery)}</strong><small>to {formatDateOnly(procurement.cargo.latest_delivery)}</small></div><div className="metric-card"><span>FREIGHT P50</span><strong>{decision ? `$${decision.forecast_p50.toFixed(2)}` : "—"}</strong><small>USD/MT</small></div><div className="metric-card"><span>RISK SCORE</span><strong>{decision ? decision.risk_score.toFixed(1) : "—"}</strong><small>0–100</small></div><div className="metric-card"><span>RECOMMENDATION</span><strong>{decision ? decision.recommendation.replace(/_/g, " ") : decisionError ? "NEEDS DATA" : "NOT RUN"}</strong><small>{decision ? (human ? `Human: ${human.action}` : "Human approval required") : decisionError ? "Decision unavailable — see error below" : "Run decision evaluation to calculate"}</small></div></div><section className="enterprise-card">{!decision && decisionError && <div className="error-banner" role="alert">{decisionError}</div>}<div className="section-head"><div><span className="eyebrow">OPTIMIZATION CONTROL</span><h2>Now vs wait</h2></div><button className="primary-button compact-button" onClick={run} disabled={busy || Boolean(submittingAction)}>{busy ? "RUNNING…" : "RUN DECISION"}</button></div><div className="control-row"><label>WAIT HORIZON <strong>{waitDays} days</strong><input type="range" min="1" max="30" value={waitDays} disabled={busy || Boolean(submittingAction)} onChange={e => setWaitDays(Number(e.target.value))}/></label></div>{decision && <div className="decision-grid"><div><span>NOW P50 COST</span><strong>${decision.now_expected_freight_cost.toLocaleString(undefined, { maximumFractionDigits: 0 })}</strong></div><div><span>WAIT CONSERVATIVE</span><strong>${decision.wait_conservative_cost.toLocaleString(undefined, { maximumFractionDigits: 0 })}</strong></div><div><span>WAIT DIFFERENCE</span><strong>${decision.wait_cost_difference.toLocaleString(undefined, { maximumFractionDigits: 0 })}</strong></div><div><span>PROBABILITY NOW &gt; BASELINE</span><strong>{(decision.probability_now_exceeds_baseline * 100).toFixed(1)}%</strong></div></div>}{error && <div className="error-banner" role="alert">{error}</div>}{actionMessage && <div className="error-banner" role="status">{actionMessage}</div>}</section>{decision && <section className="enterprise-card"><div className="section-head"><div><span className="eyebrow">HUMAN GOVERNANCE</span><h2>Approve, modify or reject</h2></div><span className="field-note">No autonomous contracting</span></div>{human && <p className="field-note">Latest saved action: {human.action} · {new Date(human.decided_at).toLocaleString("en-GB")}</p>}<div className="button-row"><button className="primary-button" onClick={() => act("APPROVE")} disabled={busy || Boolean(submittingAction) || !decision.decision_run_id}>{submittingAction === "APPROVE" ? "SAVING APPROVAL…" : "APPROVE"}</button><button className="secondary-button" onClick={() => act("MODIFY")} disabled={busy || Boolean(submittingAction) || !decision.decision_run_id}>{submittingAction === "MODIFY" ? "SAVING CHANGES…" : "MODIFY"}</button><button className="danger-button" onClick={() => act("REJECT")} disabled={busy || Boolean(submittingAction) || !decision.decision_run_id}>{submittingAction === "REJECT" ? "SAVING REJECTION…" : "REJECT"}</button></div></section>}</div>;
}

export default function App() {
  const [active, setActive] = useState("Command Center"); const [procurement, setProcurement] = useState<ProcurementContext | null>(null); const [decision, setDecision] = useState<DecisionResponse | null>(null); const [decisionError, setDecisionError] = useState(""); const [human, setHuman] = useState<HumanDecisionResponse | null>(null); const [forecast, setForecast] = useState<FreightForecastData | null>(null); const [audit, setAudit] = useState<AuditEvent[]>(() => readAudit());
  useEffect(() => {
    if (!procurement) {
      setForecast(null);
      return;
    }
    listFreightForecasts(
      procurement.cargo.origin_location_id ?? undefined,
      procurement.cargo.destination_location_id ?? undefined,
      procurement.vesselClass ?? undefined,
    )
      .then((forecasts) =>
        setForecast(
          selectVerifiedRouteForecast(forecasts, {
          originLocationId: procurement.cargo.origin_location_id,
          destinationLocationId: procurement.cargo.destination_location_id,
          vesselClass: procurement.vesselClass,
        }),
        ),
      )
      .catch(() => setForecast(null));
  }, [procurement, decision]);
  function recordAudit(event: AuditEvent) { writeAudit(event); setAudit(readAudit()); }
  async function created(p: ProcurementContext) {
    setProcurement(p);
    setDecision(null);
    setDecisionError("");
    setActive("Command Center");
    try {
      const forecasts = await listFreightForecasts(
        p.cargo.origin_location_id ?? undefined,
        p.cargo.destination_location_id ?? undefined,
        p.vesselClass ?? undefined,
      );
      const selectedForecast = selectVerifiedRouteForecast(forecasts, {
        originLocationId: p.cargo.origin_location_id,
        destinationLocationId: p.cargo.destination_location_id,
        vesselClass: p.vesselClass,
      });
      if (!selectedForecast) {
        throw new Error(
          "No verified freight forecast is available for this route and vessel class. Matching verified market observations are required; generic and simulated forecasts are not substituted.",
        );
      }
      const d = await evaluateDecision(
        p.cargo.quantity_mt,
        7,
        p.cargo.id,
        selectedForecast.id,
      );
      setDecision(d);
      setDecisionError("");
      recordAudit({ time: d.generated_at, type: "DECISION_RUN", ref: d.decision_run_id || "—", detail: `${d.recommendation} · risk ${d.risk_score.toFixed(1)} · ${d.provenance}`, procurementId: p.cargo.id });
    } catch (error) {
      setDecision(null);
      setDecisionError(error instanceof Error ? error.message : "Decision evaluation failed. Check the API and matching freight forecast, then retry RUN DECISION.");
    }
  }
  function content() { switch (active) { case "New Procurement": return <NewProcurement onCreated={created}/>; case "Market Intelligence": return <MarketIntelligence/>; case "Freight Forecast": return <FreightForecast/>; case "Container Freight": return <ContainerFreight/>; case "Port Intelligence": return <PortIntelligence/>; case "Vessel Intelligence": return <VesselDirectory/>; case "Cost & Chartering": return <CostCharting/>; case "What-If & Risk": return <WhatIfRisk decision={decision}/>; case "AI Recommendation": return <AIRecommendation procurement={procurement} decision={decision} onDecision={d => { setDecision(d); recordAudit({ time: d.generated_at, type: "DECISION_RUN", ref: d.decision_run_id || "—", detail: `${d.recommendation} · risk ${d.risk_score.toFixed(1)} · ${d.provenance}`, procurementId: procurement?.cargo.id }); }}/>; case "Decision History": return <DecisionHistory procurement={procurement} decision={decision} human={human} history={audit}/>; case "Actual Outcomes": return <ActualOutcomes procurement={procurement} decision={decision}/>; case "Model Performance": return <ModelPerformance forecast={forecast}/>; default: return <CommandCenter procurement={procurement} decision={decision} decisionError={decisionError} onDecision={d => { setDecision(d); setDecisionError(""); recordAudit({ time: d.generated_at, type: "DECISION_RUN", ref: d.decision_run_id || "—", detail: `${d.recommendation} · risk ${d.risk_score.toFixed(1)} · ${d.provenance}`, procurementId: procurement?.cargo.id }); }} human={human} onHuman={d => { setHuman(d); recordAudit({ time: d.decided_at, type: `HUMAN_${d.action}`, ref: d.id, detail: d.reason || "Human decision recorded.", procurementId: procurement?.cargo.id }); }} navigate={setActive}/>; } }
  return <div className="enterprise-app"><Sidebar active={active} onNavigate={setActive}/><main className="enterprise-main"><div className="top-status"><span><i className="status-dot"/> CONNECTED</span><span>SAIL · CHARTERPULSE AI</span></div>{content()}</main></div>;
}