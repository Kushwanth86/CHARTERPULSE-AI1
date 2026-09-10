import { useEffect, useMemo, useState } from "react";
import {
  createCargo,
  evaluateDecision,
  evaluateFeasibility,
  listCargo,
  listCountries,
  listFreightForecasts,
  listMarketObservations,
  listPorts,
  listVessels,
  recordHumanDecision,
  type CargoRequirement,
  type Country,
  type DecisionResponse,
  type FeasibilityResponse,
  type FreightForecast,
  type HumanDecisionResponse,
  type MarketObservation,
  type Port,
  type Vessel
} from "./api";

type Section =
  | "Command Center"
  | "New Procurement"
  | "Market Intelligence"
  | "Port Intelligence"
  | "Vessel Intelligence"
  | "Freight Forecast"
  | "Route & Feasibility"
  | "Cost Optimization"
  | "Charter Strategy"
  | "What-If Simulator"
  | "Risk Analysis"
  | "AI Recommendation"
  | "Inventory / Stockout"
  | "Decision History"
  | "Actual Outcomes"
  | "Model Performance";

type ProcurementSummary = {
  cargo: CargoRequirement;
  originPort: Port;
  destinationPort: Port;
  originCountry: Country;
  destinationCountry: Country;
};

const money = (value: number, currency = "USD") => new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 0 }).format(value);
const rate = (value: number) => `$${value.toFixed(2)}/MT`;
const pct = (value: number) => `${(value * 100).toFixed(1)}%`;
const dateOnly = (value?: string | null) => value ? new Date(value).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }) : "—";

const groups: { group: string; items: Section[] }[] = [
  { group: "OPERATIONS", items: ["Command Center", "New Procurement", "Market Intelligence", "Port Intelligence", "Vessel Intelligence"] },
  { group: "DECISION", items: ["Freight Forecast", "Route & Feasibility", "Cost Optimization", "Charter Strategy", "What-If Simulator", "Risk Analysis", "AI Recommendation", "Inventory / Stockout"] },
  { group: "GOVERNANCE", items: ["Decision History", "Actual Outcomes", "Model Performance"] }
];

function Field({ label, children, hint }: { label: string; children: React.ReactNode; hint?: string }) {
  return <div className="control" style={{ minWidth: 0, flex: 1 }}><label>{label}</label>{children}{hint && <div className="metric-note">{hint}</div>}</div>;
}

function Panel({ kicker, title, tag, children, className = "" }: { kicker: string; title: string; tag?: string; children: React.ReactNode; className?: string }) {
  return <section className={`panel ${className}`}><div className="panel-header"><div><div className="panel-kicker">{kicker}</div><h2>{title}</h2></div>{tag && <span className="tag">{tag}</span>}</div>{children}</section>;
}

function EmptyState({ title, text, action }: { title: string; text: string; action?: React.ReactNode }) {
  return <div className="panel" style={{ marginTop: 12 }}><div className="panel-kicker">WORKFLOW</div><h2 style={{ marginTop: 7 }}>{title}</h2><p style={{ color: "#8999ac", lineHeight: 1.7, fontSize: 11 }}>{text}</p>{action}</div>;
}

function NewProcurement({ onCreated }: { onCreated: (summary: ProcurementSummary) => void }) {
  const [countries, setCountries] = useState<Country[]>([]);
  const [materials, setMaterials] = useState<string[]>([]);
  const [originPorts, setOriginPorts] = useState<Port[]>([]);
  const [destinationPorts, setDestinationPorts] = useState<Port[]>([]);
  const [originCountryCode, setOriginCountryCode] = useState("");
  const [destinationCountryCode, setDestinationCountryCode] = useState("IN");
  const [originPortId, setOriginPortId] = useState("");
  const [destinationPortId, setDestinationPortId] = useState("");
  const [material, setMaterial] = useState("");
  const [cargoType, setCargoType] = useState("DRY_BULK");
  const [quantity, setQuantity] = useState(70000);
  const [deliveryMonth, setDeliveryMonth] = useState("2026-10");
  const [priority, setPriority] = useState("HIGH");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([listCountries(), listCargo()]).then(([countryData, cargoData]) => {
      setCountries(countryData);
      const unique = Array.from(new Set(cargoData.map((item) => item.material).filter(Boolean))).sort();
      setMaterials(unique);
      if (unique.length) setMaterial(unique.includes("Coal") ? "Coal" : unique[0]);
    }).catch((err) => setError(err instanceof Error ? err.message : "Unable to load procurement data.")).finally(() => setLoading(false));
  }, []);

  const countryCode = (country: Country) => String(country.code ?? country.country_code ?? country.iso2 ?? country.iso3 ?? "").slice(0, 2).toUpperCase();
  const originCountry = countries.find((country) => countryCode(country) === originCountryCode);
  const destinationCountry = countries.find((country) => countryCode(country) === destinationCountryCode);
  const originPort = originPorts.find((port) => port.id === originPortId);
  const destinationPort = destinationPorts.find((port) => port.id === destinationPortId);
  const deliveryDates = useMemo(() => {
    const [year, month] = deliveryMonth.split("-").map(Number);
    if (!year || !month) return null;
    const lastDay = new Date(Date.UTC(year, month, 0)).getUTCDate();
    return { earliest: `${deliveryMonth}-01T00:00:00`, latest: `${deliveryMonth}-${String(lastDay).padStart(2, "0")}T23:59:59` };
  }, [deliveryMonth]);

  useEffect(() => {
    if (!originCountryCode) { setOriginPorts([]); setOriginPortId(""); return; }
    setOriginPortId("");
    listPorts(originCountryCode).then(setOriginPorts).catch((err) => setError(err instanceof Error ? err.message : "Unable to load origin ports."));
  }, [originCountryCode]);

  useEffect(() => {
    if (!destinationCountryCode) { setDestinationPorts([]); setDestinationPortId(""); return; }
    setDestinationPortId("");
    listPorts(destinationCountryCode).then(setDestinationPorts).catch((err) => setError(err instanceof Error ? err.message : "Unable to load destination ports."));
  }, [destinationCountryCode]);

  async function submit() {
    setError("");
    if (!material || !originPort || !destinationPort || !originCountry || !destinationCountry || !deliveryDates) { setError("Select material, origin country/port, destination country/port and delivery month."); return; }
    if (originPort.id === destinationPort.id) { setError("Origin and destination ports must be different."); return; }
    setSaving(true);
    try {
      const cargo = await createCargo({ cargo_type: cargoType, material, quantity_mt: quantity, origin_location_id: originPort.location_id, destination_location_id: destinationPort.location_id, earliest_delivery: deliveryDates.earliest, latest_delivery: deliveryDates.latest, priority });
      onCreated({ cargo, originPort, destinationPort, originCountry, destinationCountry });
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to create procurement."); } finally { setSaving(false); }
  }

  return <>
    <header className="topbar"><div><div className="eyebrow">OPERATIONS / INTAKE</div><h1>New Procurement</h1></div><div className="live-status"><span className="status-dot" /> LIVE API</div></header>
    <Panel kicker="CARGO REQUIREMENT" title="From cargo requirement → to the best transportation decision" tag="USER INPUT">
      <p style={{ color: "#94a4b7", lineHeight: 1.7, fontSize: 11, maxWidth: 1000 }}>Start with what the plant actually needs. Geography is database-driven; freight price is deliberately not entered here. The saved requirement becomes the input to forecast, feasibility, cost, risk and optimization.</p>
      {loading ? <div className="simulation-note">Loading global countries and the current material catalog…</div> : <>
        <div className="content-grid" style={{ marginTop: 22 }}>
          <Field label="MATERIAL" hint="Current catalog is derived from saved cargo records until a dedicated material master is wired."><select value={material} onChange={(e) => setMaterial(e.target.value)}><option value="">Select material</option>{materials.map((item) => <option key={item}>{item}</option>)}</select></Field>
          <Field label="CARGO TYPE"><select value={cargoType} onChange={(e) => setCargoType(e.target.value)}><option value="DRY_BULK">Dry Bulk</option><option value="LIQUID_BULK">Liquid Bulk</option><option value="GENERAL_CARGO">General Cargo</option><option value="CONTAINER">Container</option><option value="RORO">RoRo</option></select></Field>
        </div>
        <div className="content-grid">
          <Field label="QUANTITY"><div className="input-row"><input type="number" min={1} value={quantity} onChange={(e) => setQuantity(Number(e.target.value))} /><span>MT</span></div></Field>
          <Field label="PRIORITY"><select value={priority} onChange={(e) => setPriority(e.target.value)}><option>LOW</option><option>NORMAL</option><option>HIGH</option><option>CRITICAL</option></select></Field>
        </div>
        <div className="content-grid">
          <Panel kicker="ORIGIN" title="Overseas supply" tag={originCountryCode || "SELECT COUNTRY"}>
            <Field label="COUNTRY"><select value={originCountryCode} onChange={(e) => setOriginCountryCode(e.target.value)}><option value="">Select country</option>{countries.map((country) => { const code = countryCode(country); return <option key={country.id} value={code}>{country.name}{code ? ` (${code})` : ""}</option>; })}</select></Field>
            <div style={{ height: 13 }} />
            <Field label="PORT" hint={originCountryCode ? `${originPorts.length} ports available from database.` : "Country first → port list loads from API."}><select value={originPortId} onChange={(e) => setOriginPortId(e.target.value)} disabled={!originCountryCode}><option value="">Select origin port</option>{originPorts.map((port) => <option key={port.id} value={port.id}>{port.name}{port.unlocode ? ` · ${port.unlocode}` : ""}</option>)}</select></Field>
          </Panel>
          <Panel kicker="DESTINATION" title="East Coast / destination" tag={destinationCountryCode || "SELECT COUNTRY"}>
            <Field label="COUNTRY"><select value={destinationCountryCode} onChange={(e) => setDestinationCountryCode(e.target.value)}><option value="">Select country</option>{countries.map((country) => { const code = countryCode(country); return <option key={country.id} value={code}>{country.name}{code ? ` (${code})` : ""}</option>; })}</select></Field>
            <div style={{ height: 13 }} />
            <Field label="PORT" hint={destinationCountryCode ? `${destinationPorts.length} ports available from database.` : "Country first → port list loads from API."}><select value={destinationPortId} onChange={(e) => setDestinationPortId(e.target.value)} disabled={!destinationCountryCode}><option value="">Select destination port</option>{destinationPorts.map((port) => <option key={port.id} value={port.id}>{port.name}{port.unlocode ? ` · ${port.unlocode}` : ""}</option>)}</select></Field>
          </Panel>
        </div>
        <div className="content-grid">
          <Field label="DELIVERY MONTH" hint="Month is converted into an earliest/latest delivery window."><input type="month" value={deliveryMonth} onChange={(e) => setDeliveryMonth(e.target.value)} /></Field>
          <div className="metric-card"><div className="metric-label">PROCUREMENT PREVIEW</div><div style={{ fontSize: 15, fontWeight: 750, marginTop: 11 }}>{originPort?.name || "Origin port"} <span style={{ color: "#6ba9de" }}>→</span> {destinationPort?.name || "Destination port"}</div><div className="metric-note">{material || "Material"} · {quantity.toLocaleString()} MT · {deliveryMonth}</div></div>
        </div>
        {error && <div className="error">{error}</div>}
        <div style={{ display: "flex", justifyContent: "flex-end" }}><button className="primary-button" onClick={submit} disabled={saving || !materials.length}>{saving ? "CREATING…" : "CREATE PROCUREMENT & OPEN COMMAND CENTER"}</button></div>
      </>}
    </Panel>
    <div className="simulation-note">Provenance rule: user-entered procurement data is stored as USER_PROVIDED. Market/forecast values are calculated downstream and retain their own provenance.</div>
  </>;
}

function CommandCenter({ procurement, decision, setDecision, humanDecision, setHumanDecision, onNavigate, onNewProcurement }: { procurement: ProcurementSummary | null; decision: DecisionResponse | null; setDecision: (value: DecisionResponse | null) => void; humanDecision: HumanDecisionResponse | null; setHumanDecision: (value: HumanDecisionResponse | null) => void; onNavigate: (section: Section) => void; onNewProcurement: () => void }) {
  const [waitDays, setWaitDays] = useState(7);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  async function runDecision() {
    if (!procurement) return;
    setLoading(true); setError(""); setHumanDecision(null);
    try { setDecision(await evaluateDecision(procurement.cargo.quantity_mt, waitDays, procurement.cargo.id)); } catch (err) { setError(err instanceof Error ? err.message : "Decision API unavailable."); } finally { setLoading(false); }
  }
  async function human(action: "APPROVE" | "MODIFY" | "REJECT") {
    if (!decision?.decision_run_id) return;
    try { setHumanDecision(await recordHumanDecision(decision.decision_run_id, action, `${action} from CHARTERPULSE Command Center.`)); } catch (err) { setError(err instanceof Error ? err.message : "Unable to save human decision."); }
  }
  if (!procurement) return <><header className="topbar"><div><div className="eyebrow">COMMAND CENTER</div><h1>Transportation Decision Intelligence</h1></div></header><EmptyState title="No active procurement" text="Create the cargo requirement first. The decision room will then carry the same cargo, route and delivery window through forecast, feasibility, cost, risk and human approval." action={<button className="primary-button" style={{ marginTop: 12 }} onClick={onNewProcurement}>OPEN NEW PROCUREMENT</button>} /></>;
  const rec = decision?.recommendation || "NOT RUN";
  return <>
    <header className="topbar"><div><div className="eyebrow">COMMAND CENTER / DECISION ROOM</div><h1>Transportation Decision Intelligence</h1></div><div className="live-status"><span className="status-dot" /> LIVE API</div></header>
    <div className="scenario-bar"><div><span className="label">ACTIVE PROCUREMENT</span><strong>{procurement.cargo.quantity_mt.toLocaleString()} MT {procurement.cargo.material.toUpperCase()}</strong></div><div className="route">{procurement.originPort.name} <span>→</span> {procurement.destinationPort.name}</div><div className="window">Delivery: <strong>{dateOnly(procurement.cargo.earliest_delivery)} – {dateOnly(procurement.cargo.latest_delivery)}</strong></div></div>
    <div className="control-panel"><Field label="WAIT HORIZON" hint="Scenario parameter, not a market price."><div className="input-row"><input type="number" min={1} max={365} value={waitDays} onChange={(e) => setWaitDays(Number(e.target.value))} /><span>DAYS</span></div></Field><div className="metric-card" style={{ minHeight: 92 }}><div className="metric-label">CARGO</div><div className="metric-value" style={{ fontSize: 20 }}>{procurement.cargo.quantity_mt.toLocaleString()} MT</div><div className="metric-note">{procurement.cargo.material} · {procurement.cargo.cargo_type}</div></div><button className="primary-button" onClick={runDecision} disabled={loading}>{loading ? "RUNNING DECISION…" : "RUN AI DECISION"}</button></div>
    {error && <div className="error">{error}</div>}
    <section className="metric-grid">
      <div className="metric-card"><div className="metric-label">FREIGHT P50</div><div className="metric-value">{decision ? rate(decision.forecast_p50) : "—"}</div><div className="metric-note">Forecast central scenario</div></div>
      <div className="metric-card"><div className="metric-label">P10 → P90 RANGE</div><div className="metric-value" style={{ fontSize: 20 }}>{decision ? `${rate(decision.forecast_p10)} → ${rate(decision.forecast_p90)}` : "—"}</div><div className="metric-note">Uncertainty, provenance {decision?.provenance || "—"}</div></div>
      <div className="metric-card"><div className="metric-label">EXPECTED NOW FREIGHT</div><div className="metric-value cost">{decision ? money(decision.now_expected_freight_cost) : "—"}</div><div className="metric-note">{procurement.cargo.quantity_mt.toLocaleString()} MT</div></div>
      <div className={`metric-card decision-card ${rec === "CHARTER_NOW" ? "positive" : ""}`}><div className="metric-label">AI RECOMMENDATION</div><div className="decision-value">{rec.replaceAll("_", " ")}</div><div className="metric-note">{decision ? `Risk ${decision.risk_score.toFixed(2)} · ${pct(decision.probability_now_exceeds_baseline)} above baseline` : "Run decision"}</div></div>
    </section>
    <div className="content-grid">
      <Panel kicker="FORECAST" title="Freight uncertainty" tag="P10 / P50 / P90"><div className="forecast-values"><div><span>P10</span><strong>{decision ? rate(decision.forecast_p10) : "—"}</strong></div><div className="featured"><span>P50</span><strong>{decision ? rate(decision.forecast_p50) : "—"}</strong></div><div><span>P90</span><strong>{decision ? rate(decision.forecast_p90) : "—"}</strong></div></div><div className="range-bar"><div className="range-fill" /><div className="range-marker p10" /><div className="range-marker p50" /><div className="range-marker p90" /></div><div className="forecast-footer"><span>Model: <strong>{decision?.model_name || "Awaiting run"}</strong></span><span>{decision?.provenance || "NO RESULT"}</span></div></Panel>
      <Panel kicker="PHYSICAL GATE" title="Route + vessel feasibility" tag="OPEN"><div className="check-list"><div><span>✓</span> Cargo requirement captured</div><div><span>✓</span> Origin: {procurement.originPort.name}</div><div><span>✓</span> Destination: {procurement.destinationPort.name}</div><div><span>✓</span> Delivery window: {dateOnly(procurement.cargo.earliest_delivery)} → {dateOnly(procurement.cargo.latest_delivery)}</div><div><span>→</span> Vessel dimensions/cargo fit: select vessel to test</div></div><button className="primary-button" style={{ marginTop: 16 }} onClick={() => onNavigate("Route & Feasibility")}>OPEN FEASIBILITY GATE</button></Panel>
    </div>
    <Panel kicker="AI RECOMMENDATION" title={rec === "NOT RUN" ? "Run the decision engine" : rec.replaceAll("_", " ")} tag={decision?.provenance || "WAITING"}><div className="recommendation-body"><div className="rationale">{(decision?.rationale || ["No recommendation yet. Run the decision engine after reviewing the procurement."]).map((item, index) => <div className="rationale-item" key={index}><span>{index + 1}</span><p>{item}</p></div>)}</div><div className="decision-actions"><div className="action-title">HUMAN DECISION</div><button className="action approve" disabled={!decision} onClick={() => human("APPROVE")}>APPROVE</button><button className="action modify" disabled={!decision} onClick={() => human("MODIFY")}>MODIFY</button><button className="action reject" disabled={!decision} onClick={() => human("REJECT")}>REJECT</button>{humanDecision && <div className="human-confirmation">✓ {humanDecision.action} recorded<br /><small>{humanDecision.id}</small></div>}</div></div></Panel>
    <div className="module-launch-grid">{["Freight Forecast", "Cost Optimization", "Charter Strategy", "What-If Simulator", "Risk Analysis", "AI Recommendation", "Inventory / Stockout", "Decision History"].map((item) => <button key={item} className="module-launch" onClick={() => onNavigate(item as Section)}>{item}<span>→</span></button>)}</div>
  </>;
}

function MarketView({ observations }: { observations: MarketObservation[] }) {
  const sorted = [...observations].sort((a, b) => new Date(b.observed_at).getTime() - new Date(a.observed_at).getTime());
  return <><Header kicker="OPERATIONS / MARKET" title="Market Intelligence" /><Panel kicker="OBSERVATIONS" title="Market data with provenance" tag={`${observations.length} RECORDS`}><p className="intro">Observed values are shown with source, timestamp and provenance. The UI never labels SIMULATED observations as live market truth.</p>{sorted.length ? <div className="table-wrap"><table><thead><tr><th>Metric</th><th>Value</th><th>Unit</th><th>Vessel</th><th>Observed</th><th>Source</th><th>Provenance</th></tr></thead><tbody>{sorted.slice(0, 25).map((item) => <tr key={item.id}><td>{item.metric}</td><td>{item.value.toFixed(2)}</td><td>{item.unit}</td><td>{item.vessel_class || "—"}</td><td>{dateOnly(item.observed_at)}</td><td>{item.source}</td><td><span className="tag">{item.provenance}</span></td></tr>)}</tbody></table></div> : <EmptyState title="No market observations returned" text="Connect an official/public market source or ingest a source-backed observation. No placeholder market value is displayed." />}</Panel></>;
}

function PortView({ procurement }: { procurement: ProcurementSummary | null }) {
  if (!procurement) return <><Header kicker="OPERATIONS / PORTS" title="Global Port Intelligence" /><EmptyState title="Create a procurement first" text="Selected origin and destination ports will appear here with coordinates, source and physical constraints." /></>;
  const ports = [procurement.originPort, procurement.destinationPort];
  return <><Header kicker="OPERATIONS / PORTS" title="Global Port Intelligence" /><div className="metric-grid">{ports.map((port) => <div className="metric-card" key={port.id}><div className="metric-label">PORT</div><div className="metric-value" style={{ fontSize: 19 }}>{port.name}</div><div className="metric-note">UN/LOCODE: {port.unlocode || "—"}</div><div className="metric-note">Coordinates: {port.latitude ?? "—"}, {port.longitude ?? "—"}</div><div className="metric-note">Source: {port.source || "—"} · {port.provenance || "—"}</div></div>)}</div><Panel kicker="INTELLIGENCE CHAIN" title="Country → location → port → operational constraints"><div className="flow-strip"><span>{procurement.originCountry.name}</span><b>→</b><span>{procurement.originPort.name}</span><b>→</b><span>Vessel / berth checks</span><b>→</b><span>{procurement.destinationPort.name}</span></div><div className="simulation-note">Port existence and physical constraints are separate concepts. Missing operational constraints remain missing; they are not inferred as safe.</div></Panel></>;
}

function VesselView({ vessels }: { vessels: Vessel[] }) {
  return <><Header kicker="OPERATIONS / FLEET" title="Vessel Intelligence" /><Panel kicker="FLEET DATA" title="Vessel particulars used by feasibility" tag={`${vessels.length} VESSELS`}><div className="table-wrap"><table><thead><tr><th>Vessel</th><th>Class</th><th>Type</th><th>DWT</th><th>LOA</th><th>Beam</th><th>Draft</th><th>Capacity</th><th>Provenance</th></tr></thead><tbody>{vessels.slice(0, 50).map((v) => <tr key={v.id}><td>{v.name}</td><td>{v.vessel_class || "—"}</td><td>{v.ship_type || "—"}</td><td>{v.dwt?.toLocaleString() || "—"}</td><td>{v.loa_m || "—"} m</td><td>{v.beam_m || "—"} m</td><td>{v.max_draft_m || "—"} m</td><td>{v.cargo_capacity_mt?.toLocaleString() || "—"} MT</td><td>{v.provenance}</td></tr>)}</tbody></table></div>{!vessels.length && <div className="simulation-note">No vessel records returned. Add source-backed vessel data before making a vessel recommendation.</div>}</Panel></>;
}

function ForecastView({ forecasts }: { forecasts: FreightForecast[] }) {
  const latest = [...forecasts].sort((a, b) => new Date(b.generated_at).getTime() - new Date(a.generated_at).getTime())[0];
  return <><Header kicker="DECISION / FORECAST" title="Freight Forecast" /><div className="metric-grid"><div className="metric-card"><div className="metric-label">P10</div><div className="metric-value">{latest ? rate(latest.p10) : "—"}</div><div className="metric-note">Downside freight scenario</div></div><div className="metric-card"><div className="metric-label">P50</div><div className="metric-value">{latest ? rate(latest.p50) : "—"}</div><div className="metric-note">Central scenario</div></div><div className="metric-card"><div className="metric-label">P90</div><div className="metric-value">{latest ? rate(latest.p90) : "—"}</div><div className="metric-note">Upside/spike scenario</div></div><div className="metric-card"><div className="metric-label">CONFIDENCE</div><div className="metric-value">{latest?.confidence != null ? pct(latest.confidence) : "—"}</div><div className="metric-note">Dynamically stored by forecast service</div></div></div><Panel kicker="MODEL EVIDENCE" title="Baseline → statistical → ML comparison"><div className="content-grid"><div className="metric-card"><div className="metric-label">CURRENT CHAMPION</div><div className="metric-value" style={{ fontSize: 18 }}>{latest?.model_name || "—"}</div><div className="metric-note">Version {latest?.model_version || "—"}</div></div><div className="metric-card"><div className="metric-label">EVALUATION</div><div className="metric-note" style={{ marginTop: 14 }}>MAE: {latest?.mae ?? "—"}</div><div className="metric-note">RMSE: {latest?.rmse ?? "—"}</div><div className="metric-note">sMAPE: {latest?.smape ?? "—"}</div><div className="metric-note">Interval coverage: {latest?.interval_coverage != null ? pct(latest.interval_coverage) : "not evaluated yet"}</div></div></div><div className="scenario-columns"><div><strong>Bearish / P10</strong><span>{latest ? rate(latest.p10) : "—"}</span></div><div><strong>Central / P50</strong><span>{latest ? rate(latest.p50) : "—"}</span></div><div><strong>Bullish / P90</strong><span>{latest ? rate(latest.p90) : "—"}</span></div></div></Panel></>;
}

function FeasibilityView({ procurement, vessels }: { procurement: ProcurementSummary | null; vessels: Vessel[] }) {
  const [vesselId, setVesselId] = useState("");
  const [result, setResult] = useState<FeasibilityResponse | null>(null);
  const [loading, setLoading] = useState(false);
  if (!procurement) return <><Header kicker="DECISION / PHYSICAL GATE" title="Route & Feasibility" /><EmptyState title="Create a procurement first" text="The physical gate requires a cargo requirement and two ports." /></>;
  const selected = vessels.find((v) => v.id === vesselId);
  async function run() { if (!selected) return; setLoading(true); try { setResult(await evaluateFeasibility({ cargo_requirement_id: procurement.cargo.id, vessel_id: selected.id, origin_port_id: procurement.originPort.id, destination_port_id: procurement.destinationPort.id })); } catch (err) { setResult({ id: "", cargo_requirement_id: procurement.cargo.id, vessel_id: selected.id, origin_port_id: procurement.originPort.id, destination_port_id: procurement.destinationPort.id, result: "ERROR", cargo_capacity_ok: null, cargo_compatibility_ok: null, origin_loa_ok: null, origin_beam_ok: null, origin_draft_ok: null, destination_loa_ok: null, destination_beam_ok: null, destination_draft_ok: null, loading_capability_ok: null, discharge_capability_ok: null, delivery_window_ok: null, reasons: [err instanceof Error ? err.message : "Feasibility API unavailable."], checks: {}, provenance: "DERIVED" }); } finally { setLoading(false); } }
  const checks = result ? Object.entries(result.checks) : [];
  return <><Header kicker="DECISION / PHYSICAL GATE" title="Route & Feasibility" /><Panel kicker="FEASIBILITY CHECKER" title="Do not let an infeasible vessel reach optimization" tag="PHYSICAL GATE"><div className="content-grid"><Field label="VESSEL"><select value={vesselId} onChange={(e) => setVesselId(e.target.value)}><option value="">Select vessel</option>{vessels.map((v) => <option key={v.id} value={v.id}>{v.name} · {v.vessel_class || "class unknown"} · {v.cargo_capacity_mt?.toLocaleString() || "?"} MT</option>)}</select></Field><div className="metric-card"><div className="metric-label">CARGO</div><div className="metric-value" style={{ fontSize: 19 }}>{procurement.cargo.quantity_mt.toLocaleString()} MT</div><div className="metric-note">{procurement.cargo.material} · {procurement.cargo.cargo_type}</div></div><button className="primary-button" onClick={run} disabled={!selected || loading}>{loading ? "CHECKING…" : "RUN PHYSICAL GATE"}</button></div><div className="flow-strip"><span>Capacity</span><b>→</b><span>Cargo fit</span><b>→</b><span>LOA / beam / draft</span><b>→</b><span>Loading / discharge</span><b>→</b><span>Delivery window</span></div>{result && <><div className={`result-banner ${result.result === "FEASIBLE" ? "ok" : "warn"}`}><strong>{result.result}</strong><span>{result.provenance}</span></div><div className="check-grid">{checks.map(([key, value]) => <div className="check-box" key={key}><span>{value === true ? "PASS" : value === false ? "FAIL" : "REVIEW"}</span><strong>{key.replaceAll("_", " ")}</strong></div>)}</div><ul className="reason-list">{result.reasons.map((reason, i) => <li key={i}>{reason}</li>)}</ul></>}</Panel></>;
}

function CostView({ procurement, decision }: { procurement: ProcurementSummary | null; decision: DecisionResponse | null }) {
  const quantity = procurement?.cargo.quantity_mt || 0;
  const components = decision ? [{ name: "Ocean freight", value: decision.now_expected_freight_cost, known: true, provenance: decision.provenance }, { name: "Bunker / fuel", value: 0, known: false, provenance: "MISSING" }, { name: "Port", value: 0, known: false, provenance: "MISSING" }, { name: "Canal", value: 0, known: false, provenance: "MISSING" }, { name: "Loading / discharge", value: 0, known: false, provenance: "MISSING" }, { name: "Demurrage", value: 0, known: false, provenance: "MISSING" }, { name: "Storage / insurance", value: 0, known: false, provenance: "MISSING" }, { name: "Delay / inland / risk", value: 0, known: false, provenance: "MISSING" }] : [];
  return <><Header kicker="DECISION / ECONOMICS" title="Total Delivered Cost" />{!decision ? <EmptyState title="Run the AI decision first" text="The cost view will use the saved freight forecast. Missing downstream components are explicitly marked missing rather than invented." /> : <><Panel kicker="LANDED COST WATERFALL" title="Known versus missing cost components" tag="PARTIAL UNTIL DATA COMPLETE"><div className="waterfall">{components.map((item) => <div className="waterfall-row" key={item.name}><div><strong>{item.name}</strong><span>{item.provenance}</span></div><div className={item.known ? "known-cost" : "missing-cost"}>{item.known ? money(item.value) : "NOT AVAILABLE"}</div></div>)}</div><div className="cost-total"><span>Known delivered-cost subtotal</span><strong>{money(decision.now_expected_freight_cost)}</strong><small>{quantity.toLocaleString()} MT · {rate(decision.now_expected_freight_cost / quantity)} · completeness is intentionally partial</small></div></Panel><div className="simulation-note">This is not a fake “total landed cost”. Ocean freight is forecast-derived; bunker, port, canal, demurrage, storage, insurance, inland and risk components require source-backed inputs before they can be included.</div></>}</>;
}

function CharterView({ decision }: { decision: DecisionResponse | null }) {
  if (!decision) return <><Header kicker="DECISION / CHARTER" title="Charter Strategy" /><EmptyState title="Run a decision first" text="The strategy screen compares charter-now versus wait using the forecast scenarios." /></>;
  const now = decision.now_expected_freight_cost;
  const wait = decision.wait_conservative_cost;
  return <><Header kicker="DECISION / CHARTER" title="Charter Strategy" /><div className="compare-grid"><div className={`strategy-card ${decision.recommendation === "CHARTER_NOW" ? "selected" : ""}`}><div className="panel-kicker">OPTION A</div><h2>CHARTER NOW</h2><div className="strategy-number">{money(now)}</div><div className="metric-note">Expected current freight exposure</div><ul><li>P50 rate: {rate(decision.forecast_p50)}</li><li>P90 exposure: {money(decision.now_p90_freight_cost)}</li><li>Risk score: {decision.risk_score.toFixed(2)}</li></ul></div><div className={`strategy-card ${decision.recommendation === "WAIT" ? "selected" : ""}`}><div className="panel-kicker">OPTION B</div><h2>WAIT</h2><div className="strategy-number">{money(wait)}</div><div className="metric-note">Conservative wait scenario</div><ul><li>Conservative rate: {rate(decision.wait_conservative_rate)}</li><li>Difference: {money(decision.wait_cost_difference)}</li><li>Difference / MT: {rate(decision.wait_cost_difference_per_mt)}</li></ul></div></div><Panel kicker="DECISION LOGIC" title="Why the strategy changed or stayed"><div className="rationale">{decision.rationale.map((x, i) => <div className="rationale-item" key={i}><span>{i + 1}</span><p>{x}</p></div>)}</div></Panel></>;
}

function WhatIfView({ decision, procurement }: { decision: DecisionResponse | null; procurement: ProcurementSummary | null }) {
  const [fuel, setFuel] = useState(0);
  const [congestion, setCongestion] = useState(0);
  const [consumption, setConsumption] = useState(0);
  if (!decision || !procurement) return <><Header kicker="DECISION / SCENARIOS" title="What-If Simulator" /><EmptyState title="Run a decision first" text="The scenario simulator needs the current forecast and procurement quantity before stress-testing the decision." /></>;
  const stressRate = decision.forecast_p50 * (1 + fuel / 100) + congestion * 0.15;
  const stressCost = stressRate * procurement.cargo.quantity_mt;
  const inventorySignal = consumption > 0 ? "Higher stockout pressure" : consumption < 0 ? "Lower stockout pressure" : "No consumption shock";
  return <><Header kicker="DECISION / SCENARIOS" title="What-If Simulator" /><Panel kicker="LIVE SCENARIO CONTROLS" title="Stress the decision before approving it" tag="SCENARIO / DERIVED"><div className="slider-grid"><Slider label="BUNKER / FUEL SHOCK" value={fuel} min={-30} max={50} unit="%" onChange={setFuel} /><Slider label="PORT CONGESTION" value={congestion} min={0} max={10} unit="days" onChange={setCongestion} /><Slider label="PLANT CONSUMPTION SHOCK" value={consumption} min={-30} max={30} unit="%" onChange={setConsumption} /></div><div className="metric-grid" style={{ marginTop: 18 }}><div className="metric-card"><div className="metric-label">STRESS FREIGHT RATE</div><div className="metric-value">{rate(stressRate)}</div><div className="metric-note">Scenario calculation from P50 + selected shocks</div></div><div className="metric-card"><div className="metric-label">STRESS FREIGHT EXPOSURE</div><div className="metric-value cost">{money(stressCost)}</div><div className="metric-note">Not a complete landed cost</div></div><div className="metric-card"><div className="metric-label">INVENTORY SIGNAL</div><div className="metric-value" style={{ fontSize: 17 }}>{inventorySignal}</div><div className="metric-note">{consumption}% consumption shock</div></div><div className="metric-card"><div className="metric-label">BASELINE</div><div className="metric-value">{rate(decision.forecast_p50)}</div><div className="metric-note">Forecast P50</div></div></div><div className="simulation-note">The congestion and fuel controls are explicit scenario assumptions. They are not represented as observed market data. A future optimizer will replace this stress proxy with source-backed bunker, port and inventory inputs.</div></Panel></>;
}

function RiskView({ decision }: { decision: DecisionResponse | null }) {
  if (!decision) return <><Header kicker="DECISION / RISK" title="Risk Analysis" /><EmptyState title="Run a decision first" text="Monte Carlo risk is calculated by the backend decision service." /></>;
  return <><Header kicker="DECISION / RISK" title="Risk Analysis" /><div className="metric-grid"><div className="metric-card"><div className="metric-label">RISK SCORE</div><div className="metric-value">{decision.risk_score.toFixed(2)}</div><div className="metric-note">Backend Monte Carlo decision risk</div></div><div className="metric-card"><div className="metric-label">P10 COST</div><div className="metric-value">{money(decision.forecast_p10 * decision.cargo_quantity_mt)}</div><div className="metric-note">Freight-only scenario</div></div><div className="metric-card"><div className="metric-label">P50 COST</div><div className="metric-value">{money(decision.forecast_p50 * decision.cargo_quantity_mt)}</div><div className="metric-note">Freight-only scenario</div></div><div className="metric-card"><div className="metric-label">P90 COST</div><div className="metric-value">{money(decision.forecast_p90 * decision.cargo_quantity_mt)}</div><div className="metric-note">Freight-only scenario</div></div></div><Panel kicker="RISK DRIVERS" title="What the current engine actually measures"><div className="check-list"><div><span>✓</span> Freight uncertainty: P10 / P50 / P90</div><div><span>✓</span> Monte Carlo simulation is persisted in the decision calculation</div><div><span>✓</span> Probability of current cost exceeding baseline: {pct(decision.probability_now_exceeds_baseline)}</div><div><span>→</span> Fuel, congestion, weather, geopolitical and contract risk require additional source inputs</div></div><div className="simulation-note">Do not interpret the current risk score as a complete maritime enterprise risk score. It is currently grounded in the available freight-risk simulation.</div></Panel></>;
}

function RecommendationView({ decision, humanDecision }: { decision: DecisionResponse | null; humanDecision: HumanDecisionResponse | null }) {
  if (!decision) return <><Header kicker="DECISION / AI" title="AI Recommendation" /><EmptyState title="No recommendation yet" text="Run the decision engine from Command Center. The recommendation will include rationale, forecast provenance and risk." /></>;
  return <><Header kicker="DECISION / AI" title="AI Recommendation" /><Panel kicker="RECOMMENDATION" title={decision.recommendation.replaceAll("_", " ")} tag={decision.provenance}><div className="metric-grid" style={{ marginTop: 18 }}><div className="metric-card"><div className="metric-label">MODEL</div><div className="metric-value" style={{ fontSize: 17 }}>{decision.model_name || "—"}</div></div><div className="metric-card"><div className="metric-label">RISK</div><div className="metric-value">{decision.risk_score.toFixed(2)}</div></div><div className="metric-card"><div className="metric-label">PROBABILITY ABOVE BASELINE</div><div className="metric-value">{pct(decision.probability_now_exceeds_baseline)}</div></div><div className="metric-card"><div className="metric-label">GENERATED</div><div className="metric-value" style={{ fontSize: 16 }}>{dateOnly(decision.generated_at)}</div></div></div><div className="rationale" style={{ marginTop: 20 }}>{decision.rationale.map((x, i) => <div className="rationale-item" key={i}><span>{i + 1}</span><p>{x}</p></div>)}</div>{decision.warnings.length > 0 && <div className="simulation-note">Warnings: {decision.warnings.join(" · ")}</div>}<div className="simulation-note">Human decision: {humanDecision ? `${humanDecision.action} recorded` : "pending"}. The system preserves the human action separately from the AI recommendation.</div></Panel></>;
}

function InventoryView({ procurement }: { procurement: ProcurementSummary | null }) {
  return <><Header kicker="DECISION / CONTINUITY" title="Inventory / Stockout" />{procurement ? <Panel kicker="STOCKPILE SAFETY" title="Inventory trajectory inputs" tag="DATA FOUNDATION"><div className="content-grid"><div className="metric-card"><div className="metric-label">CARGO ARRIVAL WINDOW</div><div className="metric-value" style={{ fontSize: 18 }}>{dateOnly(procurement.cargo.earliest_delivery)}</div><div className="metric-note">Latest: {dateOnly(procurement.cargo.latest_delivery)}</div></div><div className="metric-card"><div className="metric-label">SHIPMENT SIZE</div><div className="metric-value">{procurement.cargo.quantity_mt.toLocaleString()} MT</div><div className="metric-note">{procurement.cargo.material}</div></div></div><div className="inventory-track"><div className="safe-line">SAFE MINIMUM — inventory data required</div><div className="inventory-line"><span>Current</span><span>Expected arrival</span><span>Run-out</span></div></div><div className="simulation-note">A real stockout trajectory requires current inventory, daily consumption and expected arrival data. The interface intentionally does not invent those values.</div></Panel> : <EmptyState title="Create a procurement first" text="Inventory risk is tied to the cargo requirement and delivery window." />}</>;
}

function GovernanceView({ section, procurement, decision, humanDecision, cargos, forecasts }: { section: Section; procurement: ProcurementSummary | null; decision: DecisionResponse | null; humanDecision: HumanDecisionResponse | null; cargos: CargoRequirement[]; forecasts: FreightForecast[] }) {
  if (section === "Decision History") return <><Header kicker="GOVERNANCE" title="Decision History" /><Panel kicker="AUDIT TRAIL" title="Current decision chain" tag="SESSION + SUPABASE"><div className="history-row"><span>Procurement</span><strong>{procurement ? procurement.cargo.id : "—"}</strong><em>{procurement?.cargo.provenance || "—"}</em></div><div className="history-row"><span>AI decision</span><strong>{decision?.decision_run_id || "—"}</strong><em>{decision?.recommendation || "—"}</em></div><div className="history-row"><span>Human decision</span><strong>{humanDecision?.id || "—"}</strong><em>{humanDecision?.action || "PENDING"}</em></div><div className="simulation-note">The AI decision and human action are persisted in Supabase. This screen shows the active chain; a dedicated historical list endpoint can be added next without fabricating records.</div></Panel></>;
  if (section === "Actual Outcomes") return <><Header kicker="GOVERNANCE" title="Actual Outcomes" /><Panel kicker="CLOSED LOOP" title="Prediction → actual outcome"><div className="outcome-grid"><Field label="ACTUAL FREIGHT / MT"><input type="number" placeholder="Awaiting actual outcome" disabled /></Field><Field label="ACTUAL ARRIVAL"><input type="date" disabled /></Field><Field label="ACTUAL DELAY DAYS"><input type="number" disabled /></Field><Field label="ACTUAL TOTAL COST"><input type="number" disabled /></Field></div><div className="simulation-note">Outcome capture is intentionally shown as a governance feature but is not wired to a persistence endpoint yet. No fake actual values are inserted. This is the next backend loop after procurement/decision approval.</div></Panel></>;
  return <><Header kicker="GOVERNANCE / ML" title="Model Performance" /><Panel kicker="OBSERVED EVIDENCE" title="Forecast evaluation without fabricated accuracy"><div className="table-wrap"><table><thead><tr><th>Generated</th><th>Model</th><th>MAE</th><th>RMSE</th><th>sMAPE</th><th>Coverage</th><th>Confidence</th></tr></thead><tbody>{forecasts.slice(0, 20).map((f) => <tr key={f.id}><td>{dateOnly(f.generated_at)}</td><td>{f.model_name || "—"}</td><td>{f.mae ?? "—"}</td><td>{f.rmse ?? "—"}</td><td>{f.smape ?? "—"}</td><td>{f.interval_coverage != null ? pct(f.interval_coverage) : "Not evaluated"}</td><td>{f.confidence != null ? pct(f.confidence) : "—"}</td></tr>)}</tbody></table></div><div className="simulation-note">Actual-outcome metrics such as prediction interval coverage require observed outcomes. The interface displays “Not evaluated” instead of manufacturing a number. Loaded cargo records: {cargos.length}.</div></Panel></>;
}

function Header({ kicker, title }: { kicker: string; title: string }) { return <header className="topbar"><div><div className="eyebrow">{kicker}</div><h1>{title}</h1></div><div className="live-status"><span className="status-dot" /> LIVE API</div></header>; }
function Slider({ label, value, min, max, unit, onChange }: { label: string; value: number; min: number; max: number; unit: string; onChange: (value: number) => void }) { return <div className="slider-control"><div className="slider-head"><label>{label}</label><strong>{value > 0 ? "+" : ""}{value}{unit}</strong></div><input type="range" min={min} max={max} value={value} onChange={(e) => onChange(Number(e.target.value))} /></div>; }

function App() {
  const [activeSection, setActiveSection] = useState<Section>("New Procurement");
  const [procurement, setProcurement] = useState<ProcurementSummary | null>(null);
  const [decision, setDecision] = useState<DecisionResponse | null>(null);
  const [humanDecision, setHumanDecision] = useState<HumanDecisionResponse | null>(null);
  const [observations, setObservations] = useState<MarketObservation[]>([]);
  const [forecasts, setForecasts] = useState<FreightForecast[]>([]);
  const [vessels, setVessels] = useState<Vessel[]>([]);
  const [cargos, setCargos] = useState<CargoRequirement[]>([]);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    Promise.all([listMarketObservations(), listFreightForecasts(), listVessels(), listCargo()]).then(([market, forecast, fleet, cargo]) => {
      setObservations(market); setForecasts(forecast); setVessels(fleet); setCargos(cargo);
    }).catch((err) => setLoadError(err instanceof Error ? err.message : "Some API data could not be loaded."));
  }, []);

  function handleCreated(summary: ProcurementSummary) { setProcurement(summary); setDecision(null); setHumanDecision(null); setActiveSection("Command Center"); setCargos((current) => [summary.cargo, ...current]); }
  const nav = (section: Section) => setActiveSection(section);

  let content: React.ReactNode;
  if (activeSection === "New Procurement") content = <NewProcurement onCreated={handleCreated} />;
  else if (activeSection === "Command Center") content = <CommandCenter procurement={procurement} decision={decision} setDecision={setDecision} humanDecision={humanDecision} setHumanDecision={setHumanDecision} onNavigate={nav} onNewProcurement={() => nav("New Procurement")} />;
  else if (activeSection === "Market Intelligence") content = <MarketView observations={observations} />;
  else if (activeSection === "Port Intelligence") content = <PortView procurement={procurement} />;
  else if (activeSection === "Vessel Intelligence") content = <VesselView vessels={vessels} />;
  else if (activeSection === "Freight Forecast") content = <ForecastView forecasts={forecasts} />;
  else if (activeSection === "Route & Feasibility") content = <FeasibilityView procurement={procurement} vessels={vessels} />;
  else if (activeSection === "Cost Optimization") content = <CostView procurement={procurement} decision={decision} />;
  else if (activeSection === "Charter Strategy") content = <CharterView decision={decision} />;
  else if (activeSection === "What-If Simulator") content = <WhatIfView decision={decision} procurement={procurement} />;
  else if (activeSection === "Risk Analysis") content = <RiskView decision={decision} />;
  else if (activeSection === "AI Recommendation") content = <RecommendationView decision={decision} humanDecision={humanDecision} />;
  else if (activeSection === "Inventory / Stockout") content = <InventoryView procurement={procurement} />;
  else content = <GovernanceView section={activeSection} procurement={procurement} decision={decision} humanDecision={humanDecision} cargos={cargos} forecasts={forecasts} />;

  return <div className="app-shell"><aside className="sidebar"><div className="brand"><div className="brand-mark">CP</div><div><div className="brand-name">CHARTERPULSE</div><div className="brand-subtitle">AI DECISION INTELLIGENCE</div></div></div><nav>{groups.map((group) => <div key={group.group}><div className="nav-section">{group.group}</div>{group.items.map((item) => <button key={item} className={`nav-item ${activeSection === item ? "active" : ""}`} onClick={() => nav(item)}>{item}</button>)}</div>)}</nav><div className="sidebar-footer"><span className="status-dot" /> API {loadError ? "CHECK" : "CONNECTED"}<span className="version">MVP+</span></div></aside><main className="main">{loadError && <div className="simulation-note" style={{ marginBottom: 12 }}>Some module data could not load: {loadError}</div>}{content}<footer className="footer"><span>CHARTERPULSE AI · SIH26006</span><span>Cargo → Data → Forecast → Feasibility → Cost → Optimization → Risk → Decision → Outcome</span></footer></main></div>;
}

export default App;
