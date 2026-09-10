import type { DecisionResponse, HumanDecisionResponse } from "../api";
import type { ProcurementContext } from "./NewProcurement";

type AuditEvent = { time: string; type: string; ref: string; detail: string; procurementId?: string };

export default function DecisionHistory({ procurement, decision, human, history = [] }: { procurement: ProcurementContext | null; decision: DecisionResponse | null; human: HumanDecisionResponse | null; history?: AuditEvent[] }) {
  const events = history.length ? history : decision ? [{ time: decision.generated_at, type: "DECISION_RUN", ref: decision.decision_run_id || "—", detail: `${decision.recommendation} · risk ${decision.risk_score.toFixed(1)} · ${decision.provenance}`, procurementId: procurement?.cargo.id }] : [];
  return <div className="page-stack">
    <div className="page-heading"><div><span className="eyebrow">GOVERNANCE / AUDIT</span><h1>Decision History</h1><p>Every decision generated in this browser session is presented as a chronological audit chain. Server-side records remain the source of truth.</p></div><span className="data-badge real">AUDIT TRAIL</span></div>
    <section className="enterprise-card"><div className="audit-summary"><div><span>ACTIVE PROCUREMENT</span><strong>{procurement?.cargo.id || "No active procurement"}</strong></div><div><span>ROUTE</span><strong>{procurement ? `${procurement.originPort.name} → ${procurement.destinationPort.name}` : "—"}</strong></div><div><span>SESSION EVENTS</span><strong>{events.length}</strong></div><div><span>HUMAN ACTION</span><strong>{human?.action || "PENDING"}</strong></div></div></section>
    <section className="enterprise-card"><div className="section-head"><div><span className="eyebrow">EVENT STREAM</span><h2>Decision lifecycle</h2></div><span className="field-note">Newest first · browser audit cache</span></div>
      {events.length ? <div className="audit-timeline">{events.map((e, i) => <article className="audit-event" key={`${e.type}-${e.ref}-${i}`}><time>{new Date(e.time).toLocaleString("en-GB")}</time><strong>{e.type}</strong><div><span>{e.detail}</span><small>{e.ref}{e.procurementId ? ` · procurement ${e.procurementId}` : ""}</small></div></article>)}</div> : <div className="empty-cell">No decision run in the current browser session.</div>}
    </section>
  </div>;
}
