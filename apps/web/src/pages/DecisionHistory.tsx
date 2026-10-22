import { useEffect, useMemo, useState } from "react";
import { listHumanDecisions, type DecisionResponse, type HumanDecisionResponse } from "../api";
import type { ProcurementContext } from "./NewProcurement";

type AuditEvent = { time: string; type: string; ref: string; detail: string; procurementId?: string };

export default function DecisionHistory({ procurement, decision, human, history = [] }: { procurement: ProcurementContext | null; decision: DecisionResponse | null; human: HumanDecisionResponse | null; history?: AuditEvent[] }) {
  const [savedDecisions, setSavedDecisions] = useState<HumanDecisionResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    let active = true;
    listHumanDecisions()
      .then((items) => {
        if (active) setSavedDecisions(items);
      })
      .catch((error: unknown) => {
        if (active) setLoadError(error instanceof Error ? error.message : "Unable to load saved human decisions.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, []);

  const events = useMemo(() => {
    const sessionEvents = history.length ? history : decision ? [{
      time: decision.generated_at,
      type: "DECISION_RUN",
      ref: decision.decision_run_id || "—",
      detail: `${decision.recommendation} · risk ${decision.risk_score.toFixed(1)} · ${decision.provenance}`,
      procurementId: procurement?.cargo.id,
    }] : [];
    const persistedEvents: AuditEvent[] = savedDecisions.map((item) => ({
      time: item.decided_at,
      type: `HUMAN_${item.action}`,
      ref: item.id,
      detail: [
        item.reason || "Human decision recorded.",
        `Decision run ${item.decision_run_id}`,
        Object.keys(item.modified_parameters || {}).length
          ? `Modified: ${JSON.stringify(item.modified_parameters)}`
          : "",
      ].filter(Boolean).join(" · "),
    }));
    return [...sessionEvents, ...persistedEvents].sort(
      (a, b) => new Date(b.time).getTime() - new Date(a.time).getTime(),
    );
  }, [history, decision, procurement, savedDecisions]);

  return <div className="page-stack">
    <div className="page-heading"><div><span className="eyebrow">GOVERNANCE / AUDIT</span><h1>Decision History</h1><p>Saved human decisions are loaded from the server; decision runs generated in this browser session are also shown when available.</p></div><span className="data-badge real">AUDIT TRAIL</span></div>
    <section className="enterprise-card"><div className="audit-summary"><div><span>ACTIVE PROCUREMENT</span><strong>{procurement?.cargo.id || "No active procurement"}</strong></div><div><span>ROUTE</span><strong>{procurement ? `${procurement.originPort.name} → ${procurement.destinationPort.name}` : "—"}</strong></div><div><span>EVENTS SHOWN</span><strong>{events.length}</strong></div><div><span>LATEST HUMAN ACTION</span><strong>{savedDecisions[0]?.action || human?.action || "PENDING"}</strong></div></div></section>
    <section className="enterprise-card"><div className="section-head"><div><span className="eyebrow">EVENT STREAM</span><h2>Decision lifecycle</h2></div><span className="field-note">Newest first · server records plus session events</span></div>
      {loading && <p className="field-note" role="status">Loading saved human decisions…</p>}
      {loadError && <div className="error-banner" role="alert">Saved decision history could not be loaded: {loadError}</div>}
      {events.length ? <div className="audit-timeline">{events.map((e, i) => <article className="audit-event" key={`${e.type}-${e.ref}-${i}`}><time>{new Date(e.time).toLocaleString("en-GB")}</time><strong>{e.type}</strong><div><span>{e.detail}</span><small>{e.ref}{e.procurementId ? ` · procurement ${e.procurementId}` : ""}</small></div></article>)}</div> : !loading && <div className="empty-cell">No saved human decisions or decision runs are available.</div>}
    </section>
  </div>;
}
