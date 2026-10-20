import { useEffect, useMemo, useState } from "react";
import {
  listMonthlyFreightForecasts,
  listPorts,
  type MonthlyFreightForecast,
  type Port,
} from "../api";

const VESSEL_CLASSES = ["PANAMAX", "CAPESIZE", "HANDYSIZE", "SUPRAMAX", "ULTRAMAX"];

function MonthlyChart({ rows }: { rows: MonthlyFreightForecast[] }) {
  const min = Math.min(...rows.map(row => row.p10));
  const max = Math.max(...rows.map(row => row.p90));
  const range = Math.max(0.0001, max - min);
  const width = 900, height = 300, left = 55, right = 25, top = 20, bottom = 55;
  const x = (i: number) => left + i * ((width - left - right) / Math.max(1, rows.length - 1));
  const y = (value: number) => height - bottom - ((value - min) / range) * (height - top - bottom);
  const line = (key: "p10" | "p50" | "p90") => rows.map((row, i) => `${i ? "L" : "M"}${x(i)},${y(row[key])}`).join(" ");
  const band = [...rows.map((row, i) => `${i ? "L" : "M"}${x(i)},${y(row.p90)}`), ...rows.slice().reverse().map((row, reverseIndex) => {
    const i = rows.length - reverseIndex - 1;
    return `L${x(i)},${y(row.p10)}`;
  }), "Z"].join(" ");
  return <div className="chart-shell">
    <svg viewBox={`0 0 ${width} ${height}`} className="forecast-svg" role="img" aria-label="Monthly route-specific freight forecast with P10 to P90 interval">
      <line x1={left} x2={width-right} y1={height-bottom} y2={height-bottom} className="chart-axis"/>
      <path d={band} className="chart-line upper" opacity="0.18"/>
      <path d={line("p10")} className="chart-line lower"/>
      <path d={line("p90")} className="chart-line upper"/>
      <path d={line("p50")} className="chart-line median"/>
      {rows.map((row, i) => <text key={row.month} x={x(i)} y={height-20} className="chart-label" textAnchor="middle">{row.month}</text>)}
    </svg>
    <div className="chart-legend"><span><i className="legend-median"/>P50 median</span><span><i className="legend-band"/>P10–P90 interval</span><span>USD/MT unless stated otherwise</span></div>
  </div>;
}

export default function FreightForecast() {
  const [ports, setPorts] = useState<Port[]>([]);
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [vesselClass, setVesselClass] = useState("PANAMAX");
  const [months, setMonths] = useState(12);
  const [rows, setRows] = useState<MonthlyFreightForecast[]>([]);
  const [loadingPorts, setLoadingPorts] = useState(true);
  const [loadingForecast, setLoadingForecast] = useState(false);
  const [error, setError] = useState("");
  const [portError, setPortError] = useState("");

  useEffect(() => {
    let active = true;
    listPorts().then(items => {
      if (!active) return;
      const usable = items.filter(port => port.location_id && port.name);
      setPorts(usable);
      if (usable.length >= 2) {
        setOrigin(usable[0].location_id);
        setDestination(usable.find(port => port.location_id !== usable[0].location_id)?.location_id || "");
      } else {
        setPortError("The API did not return enough ports to select a route.");
      }
    }).catch(() => { if (active) setPortError("Could not load ports from the API."); })
      .finally(() => { if (active) setLoadingPorts(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!origin || !destination || origin === destination) {
      setRows([]);
      setError("");
      return;
    }
    let active = true;
    setLoadingForecast(true);
    setRows([]);
    setError("");
    listMonthlyFreightForecasts(origin, destination, vesselClass, months)
      .then(result => { if (active) setRows(result); })
      .catch(err => {
        if (!active) return;
        const message = err instanceof Error ? err.message : "Monthly forecast unavailable.";
        setError(message.includes("422")
          ? "No verified market observations match this port pair and vessel class. Simulated reference data is intentionally not shown as a real forecast."
          : message.includes("404")
            ? "The monthly forecast API is not available on the connected backend yet. The route-specific endpoint must be deployed before forecasts can load."
            : message);
      })
      .finally(() => { if (active) setLoadingForecast(false); });
    return () => { active = false; };
  }, [origin, destination, vesselClass, months]);

  const originPort = useMemo(() => ports.find(port => port.location_id === origin), [ports, origin]);
  const destinationPort = useMemo(() => ports.find(port => port.location_id === destination), [ports, destination]);

  return <div className="page-stack">
    <div className="page-heading"><div><span className="eyebrow">MARKET INTELLIGENCE / FORECAST</span><h1>Freight Forecast</h1><p>Monthly estimates are requested for the selected port pair and vessel class. No interpolated future values are presented as model forecasts.</p></div><span className="data-badge real">ROUTE-SCOPED</span></div>
    <section className="enterprise-card">
      <div className="section-head"><div><span className="eyebrow">FORECAST INPUTS</span><h2>Route and vessel</h2></div></div>
      <div className="filter-grid" style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(190px,1fr))",gap:"12px"}}>
        <label>Origin port<select aria-label="Origin port" value={origin} disabled={loadingPorts} onChange={event => setOrigin(event.target.value)}><option value="">Select origin</option>{ports.map(port => <option key={port.id} value={port.location_id}>{port.name}{port.unlocode ? ` (${port.unlocode})` : ""}</option>)}</select></label>
        <label>Destination port<select aria-label="Destination port" value={destination} disabled={loadingPorts} onChange={event => setDestination(event.target.value)}><option value="">Select destination</option>{ports.filter(port => port.location_id !== origin).map(port => <option key={port.id} value={port.location_id}>{port.name}{port.unlocode ? ` (${port.unlocode})` : ""}</option>)}</select></label>
        <label>Vessel class<select aria-label="Vessel class" value={vesselClass} onChange={event => setVesselClass(event.target.value)}>{VESSEL_CLASSES.map(value => <option key={value} value={value}>{value}</option>)}</select></label>
        <label>Forecast horizon<select aria-label="Forecast horizon" value={months} onChange={event => setMonths(Number(event.target.value))}><option value={3}>3 months</option><option value={6}>6 months</option><option value={12}>12 months</option><option value={24}>24 months</option></select></label>
      </div>
      {portError && <p role="alert">{portError}</p>}
      {originPort && destinationPort && <p className="forecast-meta">Route: <strong>{originPort.name}</strong> → <strong>{destinationPort.name}</strong> · Vessel: <strong>{vesselClass}</strong></p>}
    </section>
    {loadingForecast && <section className="enterprise-card"><h2>Loading monthly forecast…</h2><p>Checking for verified observations that match this route and vessel class.</p></section>}
    {!loadingForecast && error && <section className="enterprise-card"><h2>Forecast unavailable for this route</h2><p role="status">{error}</p><p>We will not substitute generic or simulated reference prices for a route-specific forecast.</p></section>}
    {!loadingForecast && !error && rows.length > 0 && <>
      <div className="metric-grid three">
        <div className="metric-card"><span>NEAR-TERM P10</span><strong>{rows[0].p10.toFixed(2)}</strong><small>{rows[0].month} · {rows[0].unit}</small></div>
        <div className="metric-card"><span>NEAR-TERM P50</span><strong>{rows[0].p50.toFixed(2)}</strong><small>{rows[0].month} · {rows[0].unit}</small></div>
        <div className="metric-card"><span>NEAR-TERM P90</span><strong>{rows[0].p90.toFixed(2)}</strong><small>{rows[0].month} · {rows[0].unit}</small></div>
      </div>
      <section className="enterprise-card"><div className="section-head"><div><span className="eyebrow">MONTHLY MODEL OUTPUT</span><h2>Freight rate forecast</h2></div></div><MonthlyChart rows={rows}/><div className="forecast-meta"><span>Input: <strong>{rows[0].input_provenance}</strong></span><span>Observations: <strong>{rows[0].observation_count}</strong></span><span>Model: <strong>{rows[0].model_name}</strong></span></div><div style={{overflowX:"auto"}}><table><thead><tr><th>Month</th><th>Horizon</th><th>P10</th><th>P50</th><th>P90</th><th>Observations</th></tr></thead><tbody>{rows.map(row => <tr key={row.month}><td>{row.month}</td><td>{row.horizon_days} days</td><td>{row.p10.toFixed(2)}</td><td>{row.p50.toFixed(2)}</td><td>{row.p90.toFixed(2)}</td><td>{row.observation_count}</td></tr>)}</tbody></table></div></section>
    </>}
    {!loadingForecast && !error && rows.length === 0 && !loadingPorts && !portError && <section className="enterprise-card"><h2>Select a route to forecast</h2><p>Choose origin, destination and vessel class to request monthly estimates.</p></section>}
  </div>;
}
