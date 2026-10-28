import { useEffect, useMemo, useState } from "react";
import { listMarketObservations, type MarketObservation } from "../api";
import { PUBLIC_MARKET_BASELINE } from "../data/publicMarket";

const money = (value: number) =>
  "$" + value.toLocaleString("en-US", { maximumFractionDigits: 2 });

export default function MarketIntelligence() {
  const [live, setLive] = useState<MarketObservation[]>([]);
  const [loadError, setLoadError] = useState("");
  const [metricFilter, setMetricFilter] = useState("ALL");
  // Verified API observations are the default; cached public proxies require opt-in.
  const [provenanceFilter, setProvenanceFilter] = useState("REAL");

  useEffect(() => {
    let cancelled = false;
    listMarketObservations()
      .then((rows) => {
        if (cancelled) return;
        setLive(rows);
        setLoadError("");
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        setLive([]);
        setLoadError(
          cause instanceof Error
            ? cause.message
            : "Unable to load market observations from the API.",
        );
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const allRows = useMemo(() => {
    const includeCachedPublicProxies =
      provenanceFilter === "ALL" || provenanceFilter === "PUBLIC_PROXY";
    const publicRows = includeCachedPublicProxies
      ? PUBLIC_MARKET_BASELINE.map((point, index) => ({
          id: "cached-public-proxy-" + index,
          market_type: "PUBLIC_REFERENCE",
          metric: point.metric,
          value: point.value,
          unit: point.unit,
          currency: point.currency,
          observed_at: point.date,
          source: point.source,
          source_reference: point.sourceUrl,
          provenance: point.provenance,
        }))
      : [];

    return [...live, ...publicRows].sort((left, right) =>
      String(right.observed_at).localeCompare(String(left.observed_at)),
    );
  }, [live, provenanceFilter]);

  const provenanceRows = useMemo(
    () =>
      allRows.filter(
        (row) =>
          provenanceFilter === "ALL" || row.provenance === provenanceFilter,
      ),
    [allRows, provenanceFilter],
  );

  const metrics = useMemo(
    () => Array.from(new Set(provenanceRows.map((row) => row.metric))),
    [provenanceRows],
  );

  const rows = useMemo(
    () =>
      provenanceRows
        .filter((row) => metricFilter === "ALL" || row.metric === metricFilter)
        .slice(0, 100),
    [provenanceRows, metricFilter],
  );

  const latest = metrics
    .map((metric) => provenanceRows.find((row) => row.metric === metric))
    .filter(Boolean) as Array<MarketObservation & { source_reference?: string | null }>;

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <span className="eyebrow">MARKET INTELLIGENCE</span>
          <h1>Market Intelligence</h1>
          <p>
            API observations are shown separately from cached public benchmarks.
            Public proxies are excluded from the default view and are never treated
            as verified route quotes.
          </p>
        </div>
        <span className="data-badge real">API DATA BY DEFAULT</span>
      </div>

      {loadError && (
        <div className="error-banner" role="alert">
          Market API unavailable: {loadError}
        </div>
      )}

      <div className="metric-grid three">
        {latest.map((row) => (
          <div className="metric-card" key={row.metric}>
            <span>{row.metric}</span>
            <strong>{row.unit === "INDEX" ? row.value.toLocaleString() : money(row.value)}</strong>
            <small>{row.observed_at} · {row.provenance}</small>
          </div>
        ))}
      </div>

      <section className="enterprise-card">
        <div className="section-head">
          <div>
            <span className="eyebrow">OBSERVATIONS</span>
            <h2>Market data with provenance</h2>
          </div>
          <span className="field-note">{rows.length} visible records</span>
        </div>

        <div className="form-grid two">
          <div className="field">
            <label>METRIC FILTER</label>
            <select value={metricFilter} onChange={(event) => setMetricFilter(event.target.value)}>
              <option value="ALL">All metrics</option>
              {metrics.map((metric) => <option key={metric} value={metric}>{metric}</option>)}
            </select>
          </div>
          <div className="field">
            <label>PROVENANCE</label>
            <select value={provenanceFilter} onChange={(event) => setProvenanceFilter(event.target.value)}>
              <option value="REAL">REAL API observations</option>
              <option value="PUBLIC_PROXY">Cached public proxies</option>
              <option value="SIMULATED">SIMULATED test data</option>
              <option value="USER_PROVIDED">USER_PROVIDED</option>
              <option value="DERIVED">DERIVED</option>
              <option value="ALL">All sources, including proxies</option>
            </select>
          </div>
        </div>

        {!rows.length && (
          <p className="field-note">
            No observations match this filter. Select PUBLIC_PROXY to inspect
            cached public benchmarks, or ALL to inspect every provenance. Those
            rows are not automatically used for route-specific decisions.
          </p>
        )}

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Metric</th>
                <th>Observed</th>
                <th>Value</th>
                <th>Unit</th>
                <th>Provenance</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td className="strong">{row.metric}</td>
                  <td>{new Date(row.observed_at).toLocaleDateString("en-GB")}</td>
                  <td>{row.unit === "INDEX" ? row.value.toLocaleString() : money(row.value)}</td>
                  <td>{row.unit}</td>
                  <td>
                    <span className={"data-badge " + (
                      row.provenance === "PUBLIC_PROXY"
                        ? "proxy"
                        : row.provenance === "REAL"
                          ? "real"
                          : "simulated"
                    )}>
                      {row.provenance}
                    </span>
                  </td>
                  <td>{row.source}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="source-strip">
          <span>PROVENANCE RULE</span>
          <strong>REAL = source-backed observations · PUBLIC_PROXY = public benchmark · SIMULATED = test data</strong>
        </div>
      </section>
    </div>
  );
}
