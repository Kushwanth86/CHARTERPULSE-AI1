import { useEffect, useMemo, useRef, useState } from "react";
import { createCargo, listCargo, listCountries, listPorts, type CargoRequirement, type Country, type Port } from "../api";
import { REFERENCE_CARGO_TYPES, REFERENCE_MATERIALS } from "../data/referenceData";
import CalendarPicker from "../components/common/CalendarPicker";

export type ProcurementContext = { cargo: CargoRequirement; originPort: Port; destinationPort: Port; originCountry: Country; destinationCountry: Country };
type Props = { onCreated: (value: ProcurementContext) => void };
type Option = { id: string; label: string; meta?: string };

const code = (c: Country) => String(c.iso2 ?? c.country_code ?? c.code ?? "").slice(0, 2).toUpperCase();

function SearchDropdown({ label, value, options, placeholder, disabled, helper, onChange }: { label: string; value: string; options: Option[]; placeholder: string; disabled?: boolean; helper?: string; onChange: (id: string) => void }) {
  const [open, setOpen] = useState(false); const [query, setQuery] = useState(""); const root = useRef<HTMLDivElement>(null); const selected = options.find(x => x.id === value);
  const filtered = useMemo(() => { const q = query.trim().toLowerCase(); return (q ? options.filter(x => `${x.label} ${x.meta || ""}`.toLowerCase().includes(q)) : options).slice(0, 80); }, [options, query]);
  useEffect(() => { const close = (e: MouseEvent) => { if (root.current && !root.current.contains(e.target as Node)) setOpen(false); }; document.addEventListener("mousedown", close); return () => document.removeEventListener("mousedown", close); }, []);
  useEffect(() => { if (!open) setQuery(""); }, [open]);
  return <div className="field search-dropdown" ref={root}>
    <label>{label}</label><button type="button" className={`search-trigger ${open ? "open" : ""}`} disabled={disabled} onClick={() => setOpen(v => !v)}><span className={selected ? "selected-label" : "placeholder-label"}>{selected?.label || placeholder}</span>{selected?.meta && <span className="selected-meta">{selected.meta}</span>}<span className="search-chevron">⌄</span></button>
    {open && <div className="search-popover"><div className="search-popover-input"><span>⌕</span><input autoFocus value={query} onChange={e => setQuery(e.target.value)} placeholder="Type to search…" /></div><div className="search-results">{filtered.map(option => <button type="button" key={option.id} className={`search-option ${option.id === value ? "selected" : ""}`} onClick={() => { onChange(option.id); setOpen(false); }}><span>{option.label}</span>{option.meta && <small>{option.meta}</small>}</button>)}{!filtered.length && <div className="search-empty">No matching records.</div>}</div><div className="search-count">Showing {filtered.length} of {options.length.toLocaleString()} records</div></div>}
    <small>{helper || "Search by name or reference code."}</small>
  </div>;
}

export default function NewProcurement({ onCreated }: Props) {
  const [countries, setCountries] = useState<Country[]>([]); const [cargoRows, setCargoRows] = useState<CargoRequirement[]>([]); const [originPorts, setOriginPorts] = useState<Port[]>([]); const [destinationPorts, setDestinationPorts] = useState<Port[]>([]);
  const [originCountry, setOriginCountry] = useState("AU"); const [destinationCountry, setDestinationCountry] = useState("IN"); const [originPort, setOriginPort] = useState(""); const [destinationPort, setDestinationPort] = useState("");
  const [material, setMaterial] = useState("Coking Coal"); const [cargoType, setCargoType] = useState("DRY_BULK"); const [quantity, setQuantity] = useState(70000); const [priority, setPriority] = useState("HIGH");
  const [fromDate, setFromDate] = useState("2026-10-01"); const [toDate, setToDate] = useState("2026-10-20"); const [error, setError] = useState(""); const [saving, setSaving] = useState(false);

  useEffect(() => { Promise.all([listCountries(), listCargo()]).then(([c, r]) => { setCountries(c); setCargoRows(r); }).catch(e => setError(e instanceof Error ? e.message : "Unable to load procurement reference data.")); }, []);
  useEffect(() => { if (!originCountry) { setOriginPorts([]); setOriginPort(""); return; } setOriginPort(""); listPorts(originCountry).then(setOriginPorts).catch(e => setError(e instanceof Error ? e.message : "Unable to load origin ports.")); }, [originCountry]);
  useEffect(() => { if (!destinationCountry) { setDestinationPorts([]); setDestinationPort(""); return; } setDestinationPort(""); listPorts(destinationCountry).then(setDestinationPorts).catch(e => setError(e instanceof Error ? e.message : "Unable to load destination ports.")); }, [destinationCountry]);

  const countriesOptions = useMemo(() => countries.filter(c => code(c)).map(c => ({ id: code(c), label: c.name, meta: `${code(c)}${c.iso3 ? ` / ${c.iso3}` : ""}` })), [countries]);
  const materialOptions = useMemo(() => Array.from(new Set([...REFERENCE_MATERIALS, ...cargoRows.map(x => x.material).filter(Boolean)])).map(x => ({ id: x, label: x, meta: "Bulk commodity" })), [cargoRows]);
  const cargoOptions = useMemo(() => { const db = cargoRows.map(x => x.cargo_type).filter(Boolean) as string[]; const refs = REFERENCE_CARGO_TYPES.map(x => x.id); return Array.from(new Set([...refs, ...db])).map(id => { const ref = REFERENCE_CARGO_TYPES.find(x => x.id === id); return { id, label: ref?.label || id.replace(/_/g, " "), meta: ref?.meta || id }; }); }, [cargoRows]);
  const originOptions = useMemo(() => originPorts.map(p => ({ id: p.id, label: p.name, meta: p.unlocode || "UN/LOCODE unavailable" })), [originPorts]); const destinationOptions = useMemo(() => destinationPorts.map(p => ({ id: p.id, label: p.name, meta: p.unlocode || "UN/LOCODE unavailable" })), [destinationPorts]);
  const op = originPorts.find(p => p.id === originPort); const dp = destinationPorts.find(p => p.id === destinationPort); const oc = countries.find(c => code(c) === originCountry); const dc = countries.find(c => code(c) === destinationCountry);

  async function submit() {
    setError(""); if (!material || !cargoType || !oc || !dc || !op || !dp) return setError("Select material, cargo type, both countries and both ports."); if (fromDate > toDate) return setError("From Date must be on or before To Date."); setSaving(true);
    try { const normalizedCargoType = cargoType.startsWith("DRY_BULK") ? "DRY_BULK" : cargoType; const cargo = await createCargo({ cargo_type: normalizedCargoType, material, quantity_mt: quantity, origin_location_id: op.location_id, destination_location_id: dp.location_id, earliest_delivery: `${fromDate}T00:00:00`, latest_delivery: `${toDate}T23:59:59`, priority }); onCreated({ cargo, originPort: op, destinationPort: dp, originCountry: oc, destinationCountry: dc }); }
    catch (e) { setError(e instanceof Error ? e.message : "Unable to create procurement."); } finally { setSaving(false); }
  }

  return <div className="page-stack">
    <div className="page-heading"><div><span className="eyebrow">OPERATIONS / PROCUREMENT</span><h1>New Procurement</h1><p>Define the cargo, trade lane and delivery window. Reference selectors are populated immediately from the frontend reference catalog and enriched by the API.</p></div><span className="data-badge proxy">REFERENCE + API</span></div>
    <section className="enterprise-card procurement-card">
      <div className="section-head"><div><span className="eyebrow">01 · CARGO REQUIREMENT</span><h2>Procurement intake</h2></div><span className="step-chip">MANDATORY INPUTS</span></div>
      <div className="form-grid three"><SearchDropdown label="MATERIAL" value={material} options={materialOptions} placeholder="Select bulk commodity" helper="Coking coal, iron ore, thermal coal and other bulk materials." onChange={setMaterial}/><SearchDropdown label="CARGO TYPE" value={cargoType} options={cargoOptions} placeholder="Select standardized cargo type" helper="Dry-bulk transport classification; vessel class labels are reference choices." onChange={setCargoType}/><div className="field"><label>QUANTITY</label><div className="input-unit"><input type="number" min="1" value={quantity} onChange={e => setQuantity(Math.max(1, Number(e.target.value)))}/><span>MT</span></div><small>Metric tonnes required.</small></div></div>
      <div className="form-divider"><span>TRADE LANE</span></div>
      <div className="form-grid two"><SearchDropdown label="ORIGIN COUNTRY" value={originCountry} options={countriesOptions} placeholder="Search country / ISO2 / ISO3" onChange={setOriginCountry}/><SearchDropdown label="ORIGIN PORT" value={originPort} options={originOptions} placeholder={originCountry ? "Search ports in selected country" : "Select origin country first"} helper={`${originOptions.length.toLocaleString()} reference/API ports available.`} disabled={!originCountry} onChange={setOriginPort}/></div>
      <div className="form-grid two"><SearchDropdown label="DESTINATION COUNTRY" value={destinationCountry} options={countriesOptions} placeholder="Search country / ISO2 / ISO3" onChange={setDestinationCountry}/><SearchDropdown label="DESTINATION PORT" value={destinationPort} options={destinationOptions} placeholder={destinationCountry ? "Search ports in selected country" : "Select destination country first"} helper={`${destinationOptions.length.toLocaleString()} reference/API ports available.`} disabled={!destinationCountry} onChange={setDestinationPort}/></div>
      <div className="calendar-window"><div className="section-head compact"><div><span className="eyebrow">02 · DELIVERY WINDOW</span><h3>Exact laycan / delivery dates</h3></div><span className="field-note">Popup calendar · inclusive dates</span></div><div className="form-grid two"><CalendarPicker label="FROM DATE" value={fromDate} onChange={setFromDate}/><CalendarPicker label="TO DATE" value={toDate} min={fromDate} onChange={setToDate}/></div><div className="date-range-readout"><span>SELECTED WINDOW</span><strong>{new Date(`${fromDate}T12:00:00`).toLocaleDateString("en-GB", { weekday: "short", day: "2-digit", month: "short", year: "numeric" })} → {new Date(`${toDate}T12:00:00`).toLocaleDateString("en-GB", { weekday: "short", day: "2-digit", month: "short", year: "numeric" })}</strong></div></div>
      <div className="form-grid two"><div className="field"><label>PRIORITY</label><select value={priority} onChange={e => setPriority(e.target.value)}><option value="LOW">Low</option><option value="MEDIUM">Medium</option><option value="HIGH">High</option><option value="CRITICAL">Critical</option></select><small>Used as procurement urgency metadata.</small></div><div className="procurement-preview"><span>LIVE REQUIREMENT PREVIEW</span><strong>{material} · {quantity.toLocaleString()} MT</strong><div>{op?.name || "Origin port"} → {dp?.name || "Destination port"}</div><small>{fromDate} → {toDate} · {priority}</small></div></div>
      {error && <div className="error-banner">{error}</div>}
      <div className="submit-row"><div><strong>Ready for decision intelligence</strong><span>Creating the requirement preserves the existing API contract and opens the decision room.</span></div><button className="primary-button" onClick={submit} disabled={saving}>{saving ? "CREATING REQUIREMENT…" : "CREATE PROCUREMENT & OPEN DECISION ROOM"}</button></div>
    </section>
  </div>;
}
