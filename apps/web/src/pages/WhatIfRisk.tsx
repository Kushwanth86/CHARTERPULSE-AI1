import { useMemo, useState } from "react";
import type { DecisionResponse } from "../api";

type Shock = { fuel: number; delay: number; consumption: number; label: string };
const presets: Shock[] = [
  { label: "Baseline", fuel: 0, delay: 0, consumption: 0 },
  { label: "Mild shock", fuel: 10, delay: 2, consumption: 5 },
  { label: "Severe shock", fuel: 25, delay: 5, consumption: 15 },
  { label: "Stress case", fuel: 40, delay: 8, consumption: 25 }
];

export default function WhatIfRisk({ decision }: { decision: DecisionResponse | null }) {
  const [selected, setSelected] = useState(1);
  const scenario = presets[selected];
  const base = decision?.now_expected_freight_cost || 0;
  const bunkerBase = base * 0.11;
  const rows = useMemo(() => {
    if (!base) return [];
    return presets.map(s => {
      const fuelImpact = bunkerBase * (s.fuel / 100);
      const delayImpact = base * 0.015 * s.delay;
      const consumptionImpact = bunkerBase * (s.consumption / 100);
      return { ...s, value: base + fuelImpact + delayImpact + consumptionImpact, fuelImpact, delayImpact, consumptionImpact };
    });
  }, [base, bunkerBase]);
  const max = Math.max(1, ...rows.map(x => x.value));
  return <div className="page-stack">
    <div className="page-heading"><div><span className="eyebrow">DECISION / RISK</span><h1>What-If & Risk</h1><p>Compare the active decision baseline with explicit market and operational shocks. This is a front-end scenario visualization; it does not alter the risk engine.</p></div><span className="data-badge proxy">DERIVED SCENARIO</span></div>
    {!decision ? <section className="enterprise-card"><h2>Run a procurement decision first</h2><p>The scenario view requires an existing decision response and never fabricates a baseline.</p></section> : <>
      <section className="enterprise-card"><div className="section-head"><div><span className="eyebrow">SHOCK LIBRARY</span><h2>Select a stress profile</h2></div><span className="field-note">No continuous sliders · explicit scenarios</span></div><div className="scenario-preset-grid">{presets.map((p, i) => <button type="button" key={p.label} className={`scenario-preset ${selected === i ? "active" : ""}`} onClick={() => setSelected(i)}><span>{p.label}</span><strong>{p.fuel}% fuel</strong><small>+{p.delay}d port · +{p.consumption}% consumption</small></button>)}</div><div className="scenario-detail"><div><span>FUEL PRICE</span><strong>+{scenario.fuel}%</strong></div><div><span>PORT DELAY</span><strong>+{scenario.delay} days</strong></div><div><span>CONSUMPTION</span><strong>+{scenario.consumption}%</strong></div></div></section>
      <section className="enterprise-card"><div className="section-head"><div><span className="eyebrow">GROUPED COST COMPARISON</span><h2>Baseline vs shock-adjusted exposure</h2></div><span className="field-note">USD · derived from current decision</span></div><div className="grouped-chart">{rows.map((r, i) => <div className="scenario-column" key={r.label}><div className="scenario-bars"><div className="bar-pair"><div className="bar-value">${base.toLocaleString(undefined, { maximumFractionDigits: 0 })}</div><div className="bar-track"><div className="bar-fill baseline" style={{ height: `${Math.max(4, base / max * 100)}%` }}/></div><span>BASE</span></div><div className="bar-pair"><div className="bar-value">${r.value.toLocaleString(undefined, { maximumFractionDigits: 0 })}</div><div className="bar-track"><div className="bar-fill scenario" style={{ height: `${Math.max(4, r.value / max * 100)}%` }}/></div><span>SHOCK</span></div></div><strong>{r.label}</strong><small>+${(r.value - base).toLocaleString(undefined, { maximumFractionDigits: 0 })}</small></div>)}</div><div className="risk-impact-grid"><div><span>ACTIVE SCENARIO</span><strong>{scenario.label}</strong></div><div><span>FUEL IMPACT</span><strong>+${rows[selected]?.fuelImpact.toLocaleString(undefined, { maximumFractionDigits: 0 })}</strong></div><div><span>DELAY IMPACT</span><strong>+${rows[selected]?.delayImpact.toLocaleString(undefined, { maximumFractionDigits: 0 })}</strong></div><div><span>TOTAL VARIANCE</span><strong>+${((rows[selected]?.value || base) - base).toLocaleString(undefined, { maximumFractionDigits: 0 })}</strong></div></div></section>
    </>}
  </div>;
}
