import { useEffect, useMemo, useRef, useState } from "react";

type Props = { label: string; value: string; min?: string; onChange: (value: string) => void };
const pad = (n: number) => String(n).padStart(2, "0");
const iso = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const fromIso = (value: string) => { const [y, m, d] = value.split("-").map(Number); return new Date(y, (m || 1) - 1, d || 1); };
const monthName = (d: Date) => d.toLocaleDateString("en-US", { month: "long", year: "numeric" });

export default function CalendarPicker({ label, value, min, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const [view, setView] = useState(() => fromIso(value || iso(new Date())));
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => { const close = (e: MouseEvent) => { if (root.current && !root.current.contains(e.target as Node)) setOpen(false); }; document.addEventListener("mousedown", close); return () => document.removeEventListener("mousedown", close); }, []);
  useEffect(() => { if (value) setView(fromIso(value)); }, [value]);
  const days = useMemo(() => { const start = new Date(view.getFullYear(), view.getMonth(), 1); const offset = (start.getDay() + 6) % 7; const count = new Date(view.getFullYear(), view.getMonth() + 1, 0).getDate(); return Array.from({ length: Math.ceil((offset + count) / 7) * 7 }, (_, i) => { const n = i - offset + 1; return n < 1 || n > count ? null : new Date(view.getFullYear(), view.getMonth(), n); }); }, [view]);
  const minValue = min ? fromIso(min) : null;
  const selected = value ? fromIso(value) : null;
  return <div className="calendar-picker" ref={root}><label>{label}</label><button type="button" className="calendar-trigger" onClick={() => setOpen(x => !x)}><span className="calendar-icon">▣</span><span>{selected ? selected.toLocaleDateString("en-GB", { weekday: "short", day: "2-digit", month: "short", year: "numeric" }) : "Select date"}</span><span className="calendar-chevron">⌄</span></button>{open && <div className="calendar-popover"><div className="calendar-toolbar"><button type="button" onClick={() => setView(new Date(view.getFullYear(), view.getMonth() - 1, 1))}>‹</button><strong>{monthName(view)}</strong><button type="button" onClick={() => setView(new Date(view.getFullYear(), view.getMonth() + 1, 1))}>›</button></div><div className="calendar-weekdays">{["MON","TUE","WED","THU","FRI","SAT","SUN"].map(d => <span key={d}>{d}</span>)}</div><div className="calendar-grid">{days.map((d, i) => { if (!d) return <span key={i} className="calendar-empty" />; const disabled = !!minValue && d < minValue; const active = !!selected && iso(d) === iso(selected); return <button key={i} type="button" disabled={disabled} className={active ? "calendar-day active" : "calendar-day"} onClick={() => { onChange(iso(d)); setOpen(false); }}>{d.getDate()}</button>; })}</div><div className="calendar-footer"><button type="button" onClick={() => { const today = iso(new Date()); if (!minValue || fromIso(today) >= minValue) onChange(today); setOpen(false); }}>Today</button></div></div>}<small>Click to open the date calendar</small></div>;
}
