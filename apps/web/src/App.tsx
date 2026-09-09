import { useEffect, useMemo, useState } from "react";
import {
  createCargo,
  evaluateDecision,
  listCargo,
  listCountries,
  listPorts,
  recordHumanDecision,
  type CargoRequirement,
  type Country,
  type DecisionResponse,
  type HumanDecisionResponse,
  type Port
} from "./api";

const money = (value: number, currency = "USD") =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 0
  }).format(value);

const rate = (value: number) => `$${value.toFixed(2)}/MT`;

type Section =
  | "Command Center"
  | "New Procurement"
  | "Market Intelligence"
  | "Port Intelligence"
  | "Vessel Intelligence"
  | "Freight Forecast"
  | "Route & Feasibility"
  | "Cost Optimization"
  | "Risk Analysis"
  | "What-If Simulator"
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

const moduleInfo: Record<Exclude<Section, "Command Center" | "New Procurement">, { kicker: string; title: string; description: string; items: string[] }> = {
  "Market Intelligence": { kicker: "OPERATIONS", title: "Market Intelligence", description: "Review market observations with source, timestamp and provenance instead of treating unverified values as live market truth.", items: ["Freight observations", "Source and freshness", "Vessel-class market context", "Forecast input history"] },
  "Port Intelligence": { kicker: "OPERATIONS", title: "Global Port Intelligence", description: "Explore the geographic foundation and port constraints used by feasibility checks.", items: ["UN/LOCODE locations", "Port dimensions and draft", "Cargo handling capability", "Operational data provenance"] },
  "Vessel Intelligence": { kicker: "OPERATIONS", title: "Vessel Intelligence", description: "Review vessel particulars and the physical attributes used to test cargo and port compatibility.", items: ["IMO / MMSI identity", "Vessel class and ship type", "DWT, LOA, beam and draft", "Cargo capacity and availability"] },
  "Freight Forecast": { kicker: "DECISION", title: "Freight Forecast", description: "View probabilistic freight forecasts rather than a single unsupported price point.", items: ["P10 / P50 / P90", "Model and version", "MAE / RMSE / sMAPE", "Forecast provenance and confidence"] },
  "Route & Feasibility": { kicker: "DECISION", title: "Route & Feasibility", description: "Check whether the selected cargo, vessel and port combination is physically feasible before optimization.", items: ["Cargo compatibility", "Capacity and stowage checks", "LOA / beam / draft constraints", "Loading, discharge and delivery window"] },
  "Cost Optimization": { kicker: "DECISION", title: "Total Delivered Cost", description: "Build the complete logistics cost picture and identify which components are known versus missing.", items: ["Ocean freight", "Bunker, port and canal costs", "Loading, discharge and demurrage", "Storage, insurance, inland and risk costs"] },
  "Risk Analysis": { kicker: "DECISION", title: "Risk Analysis", description: "Quantify uncertainty with simulation and expose the assumptions behind the risk score.", items: ["Monte Carlo simulation", "P10 / P50 / P90 cost outcomes", "Probability thresholds", "Scenario and stress testing"] },
  "What-If Simulator": { kicker: "DECISION", title: "What-If Simulator", description: "Change decision assumptions and compare charter-now versus wait scenarios without presenting forecasts as observed prices.", items: ["Wait horizon", "Cargo quantity", "Forecast quantile", "Cost and risk comparison"] },
  "Decision History": { kicker: "GOVERNANCE", title: "Decision History", description: "Trace decision runs, recommendations, assumptions and human actions stored in Supabase.", items: ["Decision run ID", "Recommendation and rationale", "Forecast / risk / cost snapshots", "Human approval, modification or rejection"] },
  "Actual Outcomes": { kicker: "GOVERNANCE", title: "Actual Outcomes", description: "Capture what actually happened after a procurement decision so forecast and decision quality can be measured.", items: ["Actual freight", "Actual delivery and delay", "Actual total logistics cost", "Decision versus outcome"] },
  "Model Performance": { kicker: "GOVERNANCE", title: "Model Performance", description: "Evaluate models using observed outcomes instead of manufacturing accuracy metrics before real outcomes exist.", items: ["MAE / RMSE / sMAPE", "Prediction interval coverage", "Forecast versus actual", "Model improvement feedback"] }
};

function Field({ label, children, hint }: { label: string; children: React.ReactNode; hint?: string }) {
  return (
    <div className="control" style={{ minWidth: 0 }}>
      <label>{label}</label>
      {children}
      {hint && <div className="metric-note" style={{ marginTop: 7 }}>{hint}</div>}
    </div>
  );
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
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const [countryData, cargoData] = await Promise.all([listCountries(), listCargo()]);
        if (cancelled) return;
        setCountries(countryData);
        const uniqueMaterials = Array.from(new Set(cargoData.map((item) => item.material).filter(Boolean))).sort();
        setMaterials(uniqueMaterials);
        if (uniqueMaterials.length > 0) setMaterial(uniqueMaterials.includes("Coal") ? "Coal" : uniqueMaterials[0]);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Unable to load procurement data.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  const countryCode = (country: Country) => String(country.code ?? country.country_code ?? country.iso2 ?? country.iso3 ?? "").slice(0, 2).toUpperCase();
  const originCountry = countries.find((country) => countryCode(country) === originCountryCode);
  const destinationCountry = countries.find((country) => countryCode(country) === destinationCountryCode);
  const originPort = originPorts.find((port) => port.id === originPortId);
  const destinationPort = destinationPorts.find((port) => port.id === destinationPortId);

  useEffect(() => {
    if (!originCountryCode) {
      setOriginPorts([]);
      setOriginPortId("");
      return;
    }
    let cancelled = false;
    setOriginPortId("");
    listPorts(originCountryCode)
      .then((ports) => { if (!cancelled) setOriginPorts(ports); })
      .catch((err) => { if (!cancelled) setError(err instanceof Error ? err.message : "Unable to load origin ports."); });
    return () => { cancelled = true; };
  }, [originCountryCode]);

  useEffect(() => {
    if (!destinationCountryCode) {
      setDestinationPorts([]);
      setDestinationPortId("");
      return;
    }
    let cancelled = false;
    setDestinationPortId("");
    listPorts(destinationCountryCode)
      .then((ports) => { if (!cancelled) setDestinationPorts(ports); })
      .catch((err) => { if (!cancelled) setError(err instanceof Error ? err.message : "Unable to load destination ports."); });
    return () => { cancelled = true; };
  }, [destinationCountryCode]);

  const deliveryDates = useMemo(() => {
    const [year, month] = deliveryMonth.split("-").map(Number);
    if (!year || !month) return null;
    const earliest = `${deliveryMonth}-01T00:00:00`;
    const lastDay = new Date(Date.UTC(year, month, 0)).getUTCDate();
    const latest = `${deliveryMonth}-${String(lastDay).padStart(2, "0")}T23:59:59`;
    return { earliest, latest };
  }, [deliveryMonth]);

  async function submit() {
    setError("");
    if (!material || !originPort || !destinationPort || !originCountry || !destinationCountry || !deliveryDates) {
      setError("Select cargo material, origin country and port, destination country and port, and delivery month.");
      return;
    }
    if (originPort.id === destinationPort.id) {
      setError("Origin and destination ports must be different.");
      return;
    }
    setSaving(true);
    try {
      const cargo = await createCargo({
        cargo_type: cargoType,
        material,
        quantity_mt: quantity,
        origin_location_id: originPort.location_id,
        destination_location_id: destinationPort.location_id,
        earliest_delivery: deliveryDates.earliest,
        latest_delivery: deliveryDates.latest,
        priority
      });
      onCreated({ cargo, originPort, destinationPort, originCountry, destinationCountry });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create procurement.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <header className="topbar">
        <div><div className="eyebrow">OPERATIONS</div><h1>New Procurement</h1></div>
        <div className="live-status"><span className="status-dot" /> LIVE API</div>
      </header>

      <section className="panel recommendation-panel" style={{ marginTop: 10 }}>
        <div className="panel-header">
          <div><div className="panel-kicker">PROCUREMENT REQUIREMENT</div><h2>Tell CHARTERPULSE what needs to move</h2></div>
          <span className="tag">USER INPUT</span>
        </div>
        <p style={{ color: "#9aabc0", lineHeight: 1.7, maxWidth: 900 }}>
          Create the cargo requirement first. Countries and ports are loaded from the platform geography data; the decision engine will use this requirement downstream.
        </p>

        {loading ? <div className="simulation-note">Loading countries and material catalog...</div> : (
          <>
            <div className="content-grid" style={{ marginTop: 22 }}>
              <Field label="MATERIAL" hint="Selected from existing cargo material records.">
                <select value={material} onChange={(e) => setMaterial(e.target.value)} disabled={!materials.length}>
                  <option value="">Select material</option>
                  {materials.map((item) => <option key={item} value={item}>{item}</option>)}
                </select>
              </Field>
              <Field label="CARGO TYPE">
                <select value={cargoType} onChange={(e) => setCargoType(e.target.value)}>
                  <option value="DRY_BULK">Dry Bulk</option>
                  <option value="LIQUID_BULK">Liquid Bulk</option>
                  <option value="GENERAL_CARGO">General Cargo</option>
                  <option value="CONTAINER">Container</option>
                </select>
              </Field>
              <Field label="QUANTITY">
                <div className="input-row"><input type="number" min={1} value={quantity} onChange={(e) => setQuantity(Number(e.target.value))} /><span>MT</span></div>
              </Field>
              <Field label="PRIORITY">
                <select value={priority} onChange={(e) => setPriority(e.target.value)}>
                  <option value="LOW">Low</option>
                  <option value="NORMAL">Normal</option>
                  <option value="HIGH">High</option>
                  <option value="CRITICAL">Critical</option>
                </select>
              </Field>
            </div>

            <div className="content-grid" style={{ marginTop: 18 }}>
              <div className="panel" style={{ margin: 0 }}>
                <div className="panel-kicker">ORIGIN</div>
                <h2 style={{ marginTop: 6 }}>Overseas supply</h2>
                <Field label="COUNTRY">
                  <select value={originCountryCode} onChange={(e) => setOriginCountryCode(e.target.value)}>
                    <option value="">Select country</option>
                    {countries.map((country) => { const code = countryCode(country); return <option key={country.id} value={code}>{country.name}{code ? ` (${code})` : ""}</option>; })}
                  </select>
                </Field>
                <div style={{ height: 12 }} />
                <Field label="PORT" hint={originCountryCode ? `${originPorts.length} ports returned for the selected country.` : "Select a country first."}>
                  <select value={originPortId} onChange={(e) => setOriginPortId(e.target.value)} disabled={!originCountryCode || !originPorts.length}>
                    <option value="">Select origin port</option>
                    {originPorts.map((port) => <option key={port.id} value={port.id}>{port.name}{port.unlocode ? ` · ${port.unlocode}` : ""}</option>)}
                  </select>
                </Field>
              </div>

              <div className="panel" style={{ margin: 0 }}>
                <div className="panel-kicker">DESTINATION</div>
                <h2 style={{ marginTop: 6 }}>East Coast India</h2>
                <Field label="COUNTRY">
                  <select value={destinationCountryCode} onChange={(e) => setDestinationCountryCode(e.target.value)}>
                    <option value="">Select country</option>
                    {countries.map((country) => { const code = countryCode(country); return <option key={country.id} value={code}>{country.name}{code ? ` (${code})` : ""}</option>; })}
                  </select>
                </Field>
                <div style={{ height: 12 }} />
                <Field label="PORT" hint={destinationCountryCode ? `${destinationPorts.length} ports returned for the selected country.` : "Select a country first."}>
                  <select value={destinationPortId} onChange={(e) => setDestinationPortId(e.target.value)} disabled={!destinationCountryCode || !destinationPorts.length}>
                    <option value="">Select destination port</option>
                    {destinationPorts.map((port) => <option key={port.id} value={port.id}>{port.name}{port.unlocode ? ` · ${port.unlocode}` : ""}</option>)}
                  </select>
                </Field>
              </div>
            </div>

            <div className="content-grid" style={{ marginTop: 18 }}>
              <Field label="DELIVERY MONTH" hint="The month becomes an earliest/latest delivery window for the cargo requirement.">
                <input type="month" value={deliveryMonth} onChange={(e) => setDeliveryMonth(e.target.value)} />
              </Field>
              <div className="metric-card" style={{ minWidth: 0 }}>
                <div className="metric-label">SELECTED ROUTE</div>
                <div style={{ marginTop: 10, fontSize: 15, fontWeight: 700 }}>{originPort?.name || "Origin port"} <span style={{ color: "#66809b" }}>→</span> {destinationPort?.name || "Destination port"}</div>
                <div className="metric-note">{deliveryMonth || "Delivery month"} · {quantity.toLocaleString()} MT · {material || "Material"}</div>
              </div>
            </div>

            {error && <div className="error" style={{ marginTop: 18 }}>{error}</div>}

            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 22 }}>
              <button className="primary-button" onClick={submit} disabled={saving || loading || !materials.length}>{saving ? "CREATING PROCUREMENT..." : "CREATE PROCUREMENT"}</button>
            </div>
          </>
        )}
      </section>

      <section className="simulation-note" style={{ marginTop: 18 }}>
        No freight price is entered here. Market price, forecast, feasibility, cost and risk are calculated downstream from the saved requirement.
      </section>
    </>
  );
}

function CommandCenter({ procurement, onNewProcurement }: { procurement: ProcurementSummary | null; onNewProcurement: () => void }) {
  const [waitDays, setWaitDays] = useState(7);
  const [decision, setDecision] = useState<DecisionResponse | null>(null);
  const [humanDecision, setHumanDecision] = useState<HumanDecisionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [humanLoading, setHumanLoading] = useState(false);
  const [error, setError] = useState("");

  async function runDecision() {
    if (!procurement) {
      setError("Create a procurement requirement first.");
      return;
    }
    setLoading(true);
    setError("");
    setHumanDecision(null);
    try {
      const result = await evaluateDecision(procurement.cargo.quantity_mt, waitDays, procurement.cargo.id);
      setDecision(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to reach the API.");
    } finally {
      setLoading(false);
    }
  }

  async function submitHumanDecision(action: "APPROVE" | "MODIFY" | "REJECT") {
    if (!decision?.decision_run_id) {
      setError("Run an AI decision before recording a human decision.");
      return;
    }
    setHumanLoading(true);
    setError("");
    try {
      const result = await recordHumanDecision(decision.decision_run_id, action, `${action} from CHARTERPULSE Command Center.`);
      setHumanDecision(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save human decision.");
    } finally {
      setHumanLoading(false);
    }
  }

  const recommendation = decision?.recommendation || "NOT RUN";

  return (
    <>
      <header className="topbar">
        <div><div className="eyebrow">COMMAND CENTER</div><h1>Transportation Decision Intelligence</h1></div>
        <div className="live-status"><span className="status-dot" /> LIVE API</div>
      </header>

      {procurement ? (
        <section className="scenario-bar">
          <div><span className="label">ACTIVE PROCUREMENT</span><strong>{procurement.cargo.quantity_mt.toLocaleString()} MT {procurement.cargo.material.toUpperCase()}</strong></div>
          <div className="route">{procurement.originPort.name} <span>→</span> {procurement.destinationPort.name}</div>
          <div className="window">Delivery: <strong>{new Date(procurement.cargo.earliest_delivery || "").toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })} – {new Date(procurement.cargo.latest_delivery || "").toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })}</strong></div>
        </section>
      ) : (
        <section className="panel recommendation-panel" style={{ marginTop: 10 }}>
          <div className="panel-kicker">NO ACTIVE PROCUREMENT</div>
          <h2 style={{ marginTop: 8 }}>Create a cargo requirement to start the decision loop.</h2>
          <p style={{ color: "#9aabc0", lineHeight: 1.7 }}>The Command Center no longer asks for raw values without context. Start with material, quantity, origin, destination and delivery window.</p>
          <button className="primary-button" style={{ marginTop: 16 }} onClick={onNewProcurement}>OPEN NEW PROCUREMENT</button>
        </section>
      )}

      {procurement && <section className="control-panel">
        <div className="control"><label>WAIT HORIZON</label><div className="input-row"><input type="number" min={1} max={365} value={waitDays} onChange={(e) => setWaitDays(Number(e.target.value))} /><span>DAYS</span></div><div className="metric-note" style={{ marginTop: 7 }}>Scenario parameter for charter-now vs wait.</div></div>
        <div className="metric-card" style={{ minWidth: 220 }}><div className="metric-label">CARGO</div><div className="metric-value" style={{ fontSize: 22 }}>{procurement.cargo.quantity_mt.toLocaleString()} MT</div><div className="metric-note">{procurement.cargo.material} · {procurement.cargo.cargo_type}</div></div>
        <button className="primary-button" onClick={runDecision} disabled={loading}>{loading ? "RUNNING MODEL..." : "RUN AI DECISION"}</button>
      </section>}

      {error && <div className="error">{error}</div>}

      {procurement && <>
        <section className="metric-grid">
          <div className="metric-card"><div className="metric-label">FREIGHT P50</div><div className="metric-value">{decision ? rate(decision.forecast_p50) : "$32.15/MT"}</div><div className="metric-note">Forecast baseline</div></div>
          <div className="metric-card"><div className="metric-label">RISK SCORE</div><div className="metric-value">{decision ? decision.risk_score.toFixed(2) : "—"}</div><div className="metric-note">Monte Carlo freight risk</div></div>
          <div className="metric-card"><div className="metric-label">EXPECTED NOW COST</div><div className="metric-value cost">{decision ? money(decision.now_expected_freight_cost) : "—"}</div><div className="metric-note">Current modeled freight</div></div>
          <div className={`metric-card decision-card ${recommendation === "CHARTER_NOW" ? "positive" : ""}`}><div className="metric-label">AI RECOMMENDATION</div><div className="decision-value">{recommendation.replaceAll("_", " ")}</div><div className="metric-note">{decision ? `${(decision.probability_now_exceeds_baseline * 100).toFixed(1)}% probability above baseline` : "Run the model to calculate"}</div></div>
        </section>

        <section className="content-grid">
          <div className="panel forecast-panel">
            <div className="panel-header"><div><div className="panel-kicker">MARKET FORECAST</div><h2>Freight uncertainty range</h2></div><span className="tag">FORECAST</span></div>
            <div className="forecast-values"><div><span>P10</span><strong>{decision ? rate(decision.forecast_p10) : "$30.09/MT"}</strong></div><div className="featured"><span>P50</span><strong>{decision ? rate(decision.forecast_p50) : "$32.15/MT"}</strong></div><div><span>P90</span><strong>{decision ? rate(decision.forecast_p90) : "$34.21/MT"}</strong></div></div>
            <div className="range-bar"><div className="range-fill" /><div className="range-marker p10" /><div className="range-marker p50" /><div className="range-marker p90" /></div>
            <div className="forecast-footer"><span>Model: <strong>{decision?.model_name || "robust_recency_trend_baseline"}</strong></span><span>Provenance: FORECAST</span></div>
          </div>
          <div className="panel feasibility-panel">
            <div className="panel-header"><div><div className="panel-kicker">ROUTE CONTEXT</div><h2>Selected ports</h2></div><span className="tag">USER INPUT</span></div>
            <div className="check-list"><div><span>✓</span> Origin: {procurement.originPort.name}</div><div><span>✓</span> Destination: {procurement.destinationPort.name}</div><div><span>✓</span> Origin country: {procurement.originCountry.name}</div><div><span>✓</span> Destination country: {procurement.destinationCountry.name}</div><div><span>✓</span> Delivery window captured</div><div><span>✓</span> Cargo requirement saved to Supabase</div></div>
            <div className="simulation-note">Port operational constraints remain source-backed intelligence; the selected route itself is user-provided.</div>
          </div>
        </section>

        <section className="panel recommendation-panel">
          <div className="panel-header"><div><div className="panel-kicker">AI RECOMMENDATION</div><h2>{recommendation === "CHARTER_NOW" ? "Charter now" : recommendation.replaceAll("_", " ")}</h2></div><div className="recommendation-badge">{recommendation.replaceAll("_", " ")}</div></div>
          <div className="recommendation-body">
            <div className="rationale">{(decision?.rationale || ["Run the AI decision after creating the procurement requirement."]).map((item, index) => <div className="rationale-item" key={index}><span>{index + 1}</span><p>{item}</p></div>)}</div>
            <div className="decision-actions"><div className="action-title">HUMAN DECISION</div><button className="action approve" disabled={humanLoading || !decision} onClick={() => submitHumanDecision("APPROVE")}>APPROVE</button><button className="action modify" disabled={humanLoading || !decision} onClick={() => submitHumanDecision("MODIFY")}>MODIFY</button><button className="action reject" disabled={humanLoading || !decision} onClick={() => submitHumanDecision("REJECT")}>REJECT</button>{humanDecision && <div className="human-confirmation">✓ {humanDecision.action} recorded<br /><small>{humanDecision.id}</small></div>}</div>
          </div>
        </section>
      </>}

      <footer className="footer"><span>CHARTERPULSE AI · SIH26006</span><span>Procurement → Forecast → Feasibility → Cost → Risk → Decision → Human approval</span></footer>
    </>
  );
}

function ModuleView({ section, onCommandCenter }: { section: Exclude<Section, "Command Center" | "New Procurement">; onCommandCenter: () => void }) {
  const info = moduleInfo[section];
  return (
    <>
      <header className="topbar"><div><div className="eyebrow">{info.kicker}</div><h1>{info.title}</h1></div><div className="live-status"><span className="status-dot" /> LIVE API</div></header>
      <section className="panel recommendation-panel" style={{ marginTop: 10 }}>
        <div className="panel-header"><div><div className="panel-kicker">CHARTERPULSE MODULE</div><h2>{info.title}</h2></div><span className="tag">MVP</span></div>
        <p style={{ color: "#9aabc0", lineHeight: 1.7, maxWidth: 850 }}>{info.description}</p>
        <div className="content-grid" style={{ marginTop: 20 }}>{info.items.map((item, index) => <div className="metric-card" key={item}><div className="metric-label">{String(index + 1).padStart(2, "0")}</div><div style={{ fontSize: 15, fontWeight: 700, marginTop: 10 }}>{item}</div><div className="metric-note">Data-driven module</div></div>)}</div>
        <div className="simulation-note" style={{ marginTop: 20 }}>This module is part of the product workflow. Its dedicated API view will use the procurement created in New Procurement.</div>
        <button className="primary-button" style={{ marginTop: 20 }} onClick={onCommandCenter}>BACK TO COMMAND CENTER</button>
      </section>
    </>
  );
}

function App() {
  const [activeSection, setActiveSection] = useState<Section>("New Procurement");
  const [procurement, setProcurement] = useState<ProcurementSummary | null>(null);
  const sections: { group: string; items: Section[] }[] = [
    { group: "OPERATIONS", items: ["Command Center", "New Procurement", "Market Intelligence", "Port Intelligence", "Vessel Intelligence"] },
    { group: "DECISION", items: ["Freight Forecast", "Route & Feasibility", "Cost Optimization", "Risk Analysis", "What-If Simulator"] },
    { group: "GOVERNANCE", items: ["Decision History", "Actual Outcomes", "Model Performance"] }
  ];

  function handleCreated(summary: ProcurementSummary) {
    setProcurement(summary);
    setActiveSection("Command Center");
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark">CP</div><div><div className="brand-name">CHARTERPULSE</div><div className="brand-subtitle">AI DECISION INTELLIGENCE</div></div></div>
        <nav>
          {sections.map((group) => <div key={group.group}>
            <div className="nav-section">{group.group}</div>
            {group.items.map((item) => <div key={item} className={`nav-item ${activeSection === item ? "active" : ""}`} onClick={() => setActiveSection(item)} role="button" tabIndex={0} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") setActiveSection(item); }}>{item}</div>)}
          </div>)}
        </nav>
        <div className="sidebar-footer"><span className="status-dot" /> API CONNECTED <span className="version">MVP</span></div>
      </aside>

      <main className="main">
        {activeSection === "New Procurement" ? <NewProcurement onCreated={handleCreated} /> : activeSection === "Command Center" ? <CommandCenter procurement={procurement} onNewProcurement={() => setActiveSection("New Procurement")} /> : <ModuleView section={activeSection} onCommandCenter={() => setActiveSection("Command Center")} />}
      </main>
    </div>
  );
}

export default App;
