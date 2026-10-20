import { useState, type FormEvent } from "react";
import { request } from "../api";

type FreightEstimate = {
  provider: string;
  estimate_type: string;
  origin: string;
  destination: string;
  loadtype: string;
  quantity: number;
  price_min: number;
  price_max: number;
  currency: string;
  transit_days_min: number | null;
  transit_days_max: number | null;
  mode: string;
  is_estimate: boolean;
  source_url: string;
};

const PORTS = [
  { value: "CNSHA", label: "Shanghai, China" },
  { value: "CNNGB", label: "Ningbo, China" },
  { value: "CNSZX", label: "Shenzhen, China" },
  { value: "CNTAO", label: "Qingdao, China" },
  { value: "CNYTN", label: "Yantian, China" },
  { value: "HKHKG", label: "Hong Kong" },
  { value: "SGSIN", label: "Singapore" },
  { value: "KRPUS", label: "Busan, South Korea" },
  { value: "JPTYO", label: "Tokyo, Japan" },
  { value: "JPOSA", label: "Osaka, Japan" },
  { value: "TWKHH", label: "Kaohsiung, Taiwan" },
  { value: "INNSA", label: "Nhava Sheva (Mumbai), India" },
  { value: "INMUN", label: "Mundra, India" },
  { value: "LKCMB", label: "Colombo, Sri Lanka" },
  { value: "AEJEA", label: "Jebel Ali, UAE" },
  { value: "NLRTM", label: "Rotterdam, Netherlands" },
  { value: "DEHAM", label: "Hamburg, Germany" },
  { value: "BEANR", label: "Antwerp, Belgium" },
  { value: "GBFXT", label: "Felixstowe, United Kingdom" },
  { value: "FRLEH", label: "Le Havre, France" },
  { value: "ESVLC", label: "Valencia, Spain" },
  { value: "ITGOA", label: "Genoa, Italy" },
  { value: "USLGB", label: "Long Beach, USA" },
  { value: "USLAX", label: "Los Angeles, USA" },
  { value: "USNYC", label: "New York, USA" },
  { value: "USORF", label: "Norfolk, USA" },
  { value: "USHOU", label: "Houston, USA" },
  { value: "CAMTR", label: "Montreal, Canada" },
  { value: "CAVAN", label: "Vancouver, Canada" },
  { value: "BRSSZ", label: "Santos, Brazil" },
  { value: "AUMEL", label: "Melbourne, Australia" },
  { value: "NZAKL", label: "Auckland, New Zealand" },
  { value: "ZADUR", label: "Durban, South Africa" },
  { value: "MYPKG", label: "Port Klang, Malaysia" },
  { value: "THLCH", label: "Laem Chabang, Thailand" },
  { value: "VNSGN", label: "Ho Chi Minh City, Vietnam" },
  { value: "IDJKT", label: "Jakarta, Indonesia" },
  { value: "PHMNL", label: "Manila, Philippines" },
  { value: "SAJED", label: "Jeddah, Saudi Arabia" },
] as const;

const CONTAINERS = [
  { value: "container20", label: "20-foot container" },
  { value: "container40", label: "40-foot container" },
  { value: "container40HC", label: "40-foot high cube" },
  { value: "container45", label: "45-foot container" },
  { value: "container45HC", label: "45-foot high cube" },
];

function money(value: number, currency: string) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(value);
}

function RouteIllustration({ origin, destination }: { origin: string; destination: string }) {
  return (
    <section className="enterprise-card">
      <div className="section-head">
        <div><span className="eyebrow">ROUTE VISUALIZATION</span><h2>Container voyage</h2></div>
        <span className="data-badge proxy">ILLUSTRATIVE</span>
      </div>
      <div className="cp-route">
        <svg className="cp-route-svg" viewBox="0 0 800 230" role="img" aria-label={`Illustrative route from ${origin} to ${destination}`}>
          <defs><linearGradient id="cpOcean" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stopColor="#0c3445"/><stop offset="100%" stopColor="#081923"/></linearGradient></defs>
          <rect width="800" height="230" rx="12" fill="url(#cpOcean)"/>
          <path d="M0 48 Q100 25 185 55 T365 49 T540 54 T800 35 M0 180 Q120 150 230 178 T450 174 T650 184 T800 165" fill="none" stroke="#1b4858" strokeWidth="1"/>
          <path d="M88 126 C220 36 330 202 430 116 S610 48 710 104" fill="none" stroke="#38bdf8" strokeOpacity=".22" strokeWidth="9"/>
          <path d="M88 126 C220 36 330 202 430 116 S610 48 710 104" fill="none" stroke="#72d7ff" strokeWidth="2.5" strokeDasharray="5 10" strokeLinecap="round"/>
          <circle cx="88" cy="126" r="8" fill="#67e8f9"/><circle cx="88" cy="126" r="16" fill="none" stroke="#67e8f9" strokeOpacity=".35"><animate attributeName="r" values="10;21;10" dur="2.4s" repeatCount="indefinite"/><animate attributeName="stroke-opacity" values=".5;0;.5" dur="2.4s" repeatCount="indefinite"/></circle>
          <circle cx="710" cy="104" r="8" fill="#34d399"/><circle cx="710" cy="104" r="16" fill="none" stroke="#34d399" strokeOpacity=".3"/>
          <g className="cp-route-ship"><text x="0" y="0" fontSize="27" textAnchor="middle">🚢</text><animateMotion dur="9s" repeatCount="indefinite" rotate="auto" path="M88 126 C220 36 330 202 430 116 S610 48 710 104"/></g>
          <g fill="#e2f3fa" fontSize="13" fontWeight="600"><text x="88" y="158" textAnchor="middle">{origin}</text><text x="710" y="136" textAnchor="middle">{destination}</text></g>
          <g fill="#78a5b8" fontSize="10"><text x="88" y="174" textAnchor="middle">ORIGIN</text><text x="710" y="152" textAnchor="middle">DESTINATION</text></g>
        </svg>
      </div>
      <p className="cp-route-note">Animated route illustration only. The ship icon does not represent a real vessel position, AIS feed, or live tracking data.</p>
    </section>
  );
}

export default function ContainerFreight() {
  const [origin, setOrigin] = useState("CNSHA");
  const [destination, setDestination] = useState("USLGB");
  const [loadtype, setLoadtype] = useState("container40");
  const [quantity, setQuantity] = useState(1);
  const [estimate, setEstimate] = useState<FreightEstimate | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function getEstimate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true); setError(""); setEstimate(null);
    const params = new URLSearchParams({
      origin: origin.trim().toUpperCase(),
      destination: destination.trim().toUpperCase(),
      loadtype,
      quantity: String(quantity),
    });
    try {
      setEstimate(await request<FreightEstimate>(`/api/v1/freightos/estimate?${params.toString()}`));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to retrieve a Freightos estimate. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page-stack cp-container-page">
      <header className="page-heading">
        <div><span className="eyebrow">OPERATIONS / CONTAINER SHIPPING</span><h1>Container Freight</h1><p>Request an indicative container shipping rate and transit-time range from Freightos, separate from bulk freight forecasts.</p></div>
        <span className="data-badge real">FREIGHTOS ESTIMATE</span>
      </header>
      <section className="hero-command cp-container-hero">
        <div><span className="eyebrow">CONTAINER RATE INTELLIGENCE</span><h2>Estimate the cost of your next container shipment.</h2><p>Enter port codes and container quantity to request a rate range.</p></div>
        <div className="cp-hero-mark" aria-hidden="true">↗</div>
      </section>
      <section className="enterprise-card">
        <div className="section-head"><div><span className="eyebrow">SHIPMENT PARAMETERS</span><h2>Configure your route</h2></div><span className="field-note">UN/LOCODE format</span></div>
        <form onSubmit={getEstimate}>
          <div className="form-grid two">
            <div className="field"><label htmlFor="cp-origin">ORIGIN PORT CODE</label><select id="cp-origin" value={origin} onChange={e => setOrigin(e.target.value)} required><option value="" disabled>Select origin port</option>{PORTS.map(port => <option key={port.value} value={port.value}>{port.value} — {port.label}</option>)}</select><small>{PORTS.length} available ports · choose origin</small></div>
            <div className="field"><label htmlFor="cp-destination">DESTINATION PORT CODE</label><select id="cp-destination" value={destination} onChange={e => setDestination(e.target.value)} required><option value="" disabled>Select destination port</option>{PORTS.map(port => <option key={port.value} value={port.value}>{port.value} — {port.label}</option>)}</select><small>{PORTS.length} available ports · choose destination</small></div>
          </div>
          <div className="form-grid two">
            <div className="field"><label htmlFor="cp-container-type">CONTAINER TYPE</label><select id="cp-container-type" value={loadtype} onChange={e => setLoadtype(e.target.value)}>{CONTAINERS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}</select></div>
            <div className="field"><label htmlFor="cp-quantity">NUMBER OF CONTAINERS</label><input id="cp-quantity" type="number" min={1} max={20} step={1} value={quantity} onChange={e => setQuantity(Number(e.target.value))} required/></div>
          </div>
          {error && <div className="error-banner">{error}</div>}
          <div className="button-row cp-submit-row"><button className="primary-button" type="submit" disabled={busy || !origin.trim() || !destination.trim() || quantity < 1}>{busy ? "REQUESTING ESTIMATE…" : "GET CONTAINER ESTIMATE"}</button></div>
        </form>
      </section>
      <RouteIllustration origin={origin || "ORIGIN"} destination={destination || "DESTINATION"}/>
      {estimate ? <>
        <section className="metric-grid three">
          <div className="metric-card cp-price-card"><span>ESTIMATED PRICE RANGE</span><strong>{money(estimate.price_min, estimate.currency)}</strong><small>to {money(estimate.price_max, estimate.currency)} · provider-returned range</small></div>
          <div className="metric-card"><span>MINIMUM TRANSIT TIME</span><strong>{estimate.transit_days_min == null ? "—" : `${estimate.transit_days_min} days`}</strong><small>Provider estimate</small></div>
          <div className="metric-card"><span>MAXIMUM TRANSIT TIME</span><strong>{estimate.transit_days_max == null ? "—" : `${estimate.transit_days_max} days`}</strong><small>Provider estimate</small></div>
        </section>
        <section className="enterprise-card">
          <div className="section-head"><div><span className="eyebrow">ESTIMATE DETAILS</span><h2>{estimate.origin} → {estimate.destination}</h2></div><span className="data-badge proxy">{estimate.mode}</span></div>
          <div className="decision-grid">
            <div><span>CONTAINER TYPE</span><strong>{estimate.loadtype}</strong></div><div><span>QUANTITY</span><strong>{estimate.quantity}</strong></div><div><span>PROVIDER</span><strong>{estimate.provider}</strong></div><div><span>DATA TYPE</span><strong>Estimate only</strong></div>
          </div>
          <div className="source-strip"><span>SOURCE</span><a href={estimate.source_url || "https://ship.freightos.com"} target="_blank" rel="noreferrer">Freightos shipping calculator ↗</a><p>Rates and transit times are indicative and may change. Confirm the final quote, inclusions, and validity with the provider before making a shipping decision.</p></div>
        </section>
      </> : <div className="source-strip"><span>PROVIDER</span>Freightos estimate service · Results appear here after a successful request.<p><a href="https://ship.freightos.com" target="_blank" rel="noreferrer">Open Freightos shipping calculator ↗</a></p></div>}
    </div>
  );
}
