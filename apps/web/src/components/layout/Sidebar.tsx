import { useState, type ReactNode } from "react";

export type NavItem = { id: string; label: string; icon: ReactNode };
export type NavGroup = { title: string; items: NavItem[] };

const icons: Record<string, ReactNode> = {
  dashboard: <span>⌂</span>, container: <span>▤</span>, procurement: <span>＋</span>, market: <span>◒</span>, forecast: <span>⌁</span>, port: <span>⚓</span>, vessel: <span>◈</span>, cost: <span>Σ</span>, risk: <span>◇</span>, ai: <span>✦</span>, history: <span>↺</span>, outcomes: <span>✓</span>, model: <span>◌</span>
};

export const navGroups: NavGroup[] = [
  { title: "OPERATIONS", items: ["Command Center", "New Procurement", "Market Intelligence", "Freight Forecast", "Container Freight", "Port Intelligence", "Vessel Intelligence"].map((label) => ({ id: label, label, icon: label === "Container Freight" ? icons.container : ({ "Command Center": icons.dashboard, "New Procurement": icons.procurement, "Market Intelligence": icons.market, "Freight Forecast": icons.forecast, "Port Intelligence": icons.port, "Vessel Intelligence": icons.vessel } as Record<string, ReactNode>)[label] })) },
  { title: "DECISION", items: ["Cost & Chartering", "What-If & Risk", "AI Recommendation"].map((label, i) => ({ id: label, label, icon: Object.values(icons)[6 + i] })) },
  { title: "GOVERNANCE", items: ["Decision History", "Actual Outcomes", "Model Performance"].map((label, i) => ({ id: label, label, icon: Object.values(icons)[9 + i] })) }
];

export default function Sidebar({ active, onNavigate }: { active: string; onNavigate: (id: string) => void }) {
  const [collapsed, setCollapsed] = useState(false);
  return <aside className={collapsed ? "enterprise-sidebar is-collapsed" : "enterprise-sidebar"}>
    <div className="brand"><div className="brand-mark" aria-hidden="true"><svg viewBox="0 0 48 48" role="img"><defs><linearGradient id="cpPulse" x1="0" x2="1"><stop offset="0" stopColor="#b8e6c2"/><stop offset="1" stopColor="#5cb77b"/></linearGradient></defs><path d="M24 4 40 10v13c0 10-6.8 16.2-16 20C14.8 39.2 8 33 8 23V10L24 4Z" fill="none" stroke="url(#cpPulse)" strokeWidth="2"/><path d="M11 27h26l-4 6H15l-4-6Z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round"/><path d="M14 24c3-4 6-4 10 0 3-4 6-4 10 0" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"/><path d="M14 18h20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity=".65"/></svg></div><div className="brand-copy"><strong>CharterPulse AI</strong><span>MARITIME · DECISION INTELLIGENCE</span></div><button className="sidebar-toggle" type="button" aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} aria-expanded={!collapsed} onClick={() => setCollapsed(value => !value)}>{collapsed ? "»" : "«"}</button></div>
    <div className="sidebar-status"><span className="status-dot"/><span className="sidebar-status-copy"> DATA FABRIC ONLINE</span></div>
    <nav aria-label="Main navigation">{navGroups.map(group => <div className="nav-group" key={group.title}><div className="nav-group-title">{group.title}</div>{group.items.map(item => <button key={item.id} title={collapsed ? item.label : undefined} aria-current={active === item.id ? "page" : undefined} className={active === item.id ? "nav-item active" : "nav-item"} onClick={() => onNavigate(item.id)}><span className="nav-icon">{item.icon}</span><span className="nav-label">{item.label}</span></button>)}</div>)}</nav>
    <div className="sidebar-footer"><div>SAIL PROCUREMENT DESK</div><small>Decision support · human approval required</small></div>
  </aside>;
}
