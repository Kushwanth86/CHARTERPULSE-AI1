import type { ReactNode } from "react";

export type NavItem = { id: string; label: string; icon: ReactNode };
export type NavGroup = { title: string; items: NavItem[] };

const icons: Record<string, ReactNode> = {
  dashboard: <span>⌂</span>, procurement: <span>＋</span>, market: <span>◒</span>, forecast: <span>⌁</span>, port: <span>⚓</span>, vessel: <span>◈</span>, cost: <span>Σ</span>, risk: <span>◇</span>, ai: <span>✦</span>, history: <span>↺</span>, outcomes: <span>✓</span>, model: <span>◌</span>
};

export const navGroups: NavGroup[] = [
  { title: "OPERATIONS", items: ["Command Center", "New Procurement", "Market Intelligence", "Freight Forecast", "Port Intelligence", "Vessel Intelligence"].map((label, i) => ({ id: label, label, icon: Object.values(icons)[i] })) },
  { title: "DECISION", items: ["Cost & Chartering", "What-If & Risk", "AI Recommendation"].map((label, i) => ({ id: label, label, icon: Object.values(icons)[6 + i] })) },
  { title: "GOVERNANCE", items: ["Decision History", "Actual Outcomes", "Model Performance"].map((label, i) => ({ id: label, label, icon: Object.values(icons)[9 + i] })) }
];

export default function Sidebar({ active, onNavigate }: { active: string; onNavigate: (id: string) => void }) {
  return <aside className="enterprise-sidebar"><div className="brand"><div className="brand-mark" aria-hidden="true"><svg viewBox="0 0 44 44" role="img"><path d="M22 4 38 12v13c0 9-6.5 13-16 15C12.5 38 6 34 6 25V12L22 4Z" fill="none" stroke="currentColor" strokeWidth="2"/><path d="M11 25h22M14 20h16M18 15h8" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/><path d="M15 30c2.7-2 5-2 7 0 2-2 4.3-2 7 0" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg></div><div><strong>CharterPulse</strong><span>AI · DECISION INTELLIGENCE</span></div></div><div className="sidebar-status"><span className="status-dot"/> DATA FABRIC ONLINE</div><nav>{navGroups.map(group => <div className="nav-group" key={group.title}><div className="nav-group-title">{group.title}</div>{group.items.map(item => <button key={item.id} className={active === item.id ? "nav-item active" : "nav-item"} onClick={() => onNavigate(item.id)}><span className="nav-icon">{item.icon}</span><span>{item.label}</span></button>)}</div>)}</nav><div className="sidebar-footer"><div>SAIL PROCUREMENT DESK</div><small>Decision support · human approval required</small></div></aside>;
}
