import { useState } from "react";
import {
  evaluateDecision,
  recordHumanDecision,
  type DecisionResponse,
  type HumanDecisionResponse
} from "./api";

const money = (value: number, currency = "USD") =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 0
  }).format(value);

const rate = (value: number) =>
  `$${value.toFixed(2)}/MT`;

function App() {
  const [cargoQuantity, setCargoQuantity] = useState(70000);
  const [waitDays, setWaitDays] = useState(7);
  const [decision, setDecision] = useState<DecisionResponse | null>(null);
  const [humanDecision, setHumanDecision] =
    useState<HumanDecisionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [humanLoading, setHumanLoading] = useState(false);
  const [error, setError] = useState("");

  async function runDecision() {
    setLoading(true);
    setError("");
    setHumanDecision(null);

    try {
      const result = await evaluateDecision(cargoQuantity, waitDays);
      setDecision(result);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to reach the API."
      );
    } finally {
      setLoading(false);
    }
  }

  async function submitHumanDecision(
    action: "APPROVE" | "MODIFY" | "REJECT"
  ) {
    if (!decision?.decision_run_id) {
      setError("Run an AI decision before recording a human decision.");
      return;
    }

    setHumanLoading(true);
    setError("");

    try {
      const result = await recordHumanDecision(
        decision.decision_run_id,
        action,
        `${action} from CHARTERPULSE Command Center.`
      );
      setHumanDecision(result);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to save human decision."
      );
    } finally {
      setHumanLoading(false);
    }
  }

  const recommendation = decision?.recommendation || "NOT RUN";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">CP</div>
          <div>
            <div className="brand-name">CHARTERPULSE</div>
            <div className="brand-subtitle">AI DECISION INTELLIGENCE</div>
          </div>
        </div>

        <nav>
          <div className="nav-section">OPERATIONS</div>
          <div className="nav-item active">Command Center</div>
          <div className="nav-item">New Procurement</div>
          <div className="nav-item">Market Intelligence</div>
          <div className="nav-item">Port Intelligence</div>
          <div className="nav-item">Vessel Intelligence</div>

          <div className="nav-section">DECISION</div>
          <div className="nav-item">Freight Forecast</div>
          <div className="nav-item">Route & Feasibility</div>
          <div className="nav-item">Cost Optimization</div>
          <div className="nav-item">Risk Analysis</div>
          <div className="nav-item">What-If Simulator</div>

          <div className="nav-section">GOVERNANCE</div>
          <div className="nav-item">Decision History</div>
          <div className="nav-item">Actual Outcomes</div>
          <div className="nav-item">Model Performance</div>
        </nav>

        <div className="sidebar-footer">
          <span className="status-dot" />
          API CONNECTED
          <span className="version">MVP</span>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <div className="eyebrow">COMMAND CENTER</div>
            <h1>Transportation Decision Intelligence</h1>
          </div>
          <div className="live-status">
            <span className="status-dot" />
            LIVE API
          </div>
        </header>

        <section className="scenario-bar">
          <div>
            <span className="label">ACTIVE SCENARIO</span>
            <strong>70,000 MT COAL PROCUREMENT</strong>
          </div>
          <div className="route">
            Overseas Supply <span>→</span> East Coast India
          </div>
          <div className="window">
            Delivery: <strong>01–20 OCT 2026</strong>
          </div>
        </section>

        <section className="control-panel">
          <div className="control">
            <label>CARGO QUANTITY</label>
            <div className="input-row">
              <input
                type="number"
                value={cargoQuantity}
                onChange={(e) => setCargoQuantity(Number(e.target.value))}
              />
              <span>MT</span>
            </div>
          </div>

          <div className="control">
            <label>WAIT HORIZON</label>
            <div className="input-row">
              <input
                type="number"
                min={1}
                max={365}
                value={waitDays}
                onChange={(e) => setWaitDays(Number(e.target.value))}
              />
              <span>DAYS</span>
            </div>
          </div>

          <button
            className="primary-button"
            onClick={runDecision}
            disabled={loading}
          >
            {loading ? "RUNNING MODEL..." : "RUN AI DECISION"}
          </button>
        </section>

        {error && <div className="error">{error}</div>}

        <section className="metric-grid">
          <div className="metric-card">
            <div className="metric-label">FREIGHT P50</div>
            <div className="metric-value">
              {decision ? rate(decision.forecast_p50) : "$32.15/MT"}
            </div>
            <div className="metric-note">Forecast baseline</div>
          </div>

          <div className="metric-card">
            <div className="metric-label">RISK SCORE</div>
            <div className="metric-value">
              {decision ? decision.risk_score.toFixed(2) : "23.57"}
            </div>
            <div className="metric-note">Monte Carlo freight risk</div>
          </div>

          <div className="metric-card">
            <div className="metric-label">EXPECTED NOW COST</div>
            <div className="metric-value cost">
              {decision
                ? money(decision.now_expected_freight_cost)
                : "$2.25M"}
            </div>
            <div className="metric-note">Current modeled freight</div>
          </div>

          <div className={`metric-card decision-card ${
            recommendation === "CHARTER_NOW" ? "positive" : ""
          }`}>
            <div className="metric-label">AI RECOMMENDATION</div>
            <div className="decision-value">
              {recommendation.replaceAll("_", " ")}
            </div>
            <div className="metric-note">
              {decision
                ? `${(decision.probability_now_exceeds_baseline * 100).toFixed(1)}% probability above baseline`
                : "Run the model to calculate"}
            </div>
          </div>
        </section>

        <section className="content-grid">
          <div className="panel forecast-panel">
            <div className="panel-header">
              <div>
                <div className="panel-kicker">MARKET FORECAST</div>
                <h2>Freight uncertainty range</h2>
              </div>
              <span className="tag">FORECAST</span>
            </div>

            <div className="forecast-values">
              <div>
                <span>P10</span>
                <strong>
                  {decision ? rate(decision.forecast_p10) : "$30.09/MT"}
                </strong>
              </div>
              <div className="featured">
                <span>P50</span>
                <strong>
                  {decision ? rate(decision.forecast_p50) : "$32.15/MT"}
                </strong>
              </div>
              <div>
                <span>P90</span>
                <strong>
                  {decision ? rate(decision.forecast_p90) : "$34.21/MT"}
                </strong>
              </div>
            </div>

            <div className="range-bar">
              <div className="range-fill" />
              <div className="range-marker p10" />
              <div className="range-marker p50" />
              <div className="range-marker p90" />
            </div>

            <div className="forecast-footer">
              <span>
                Model:{" "}
                <strong>
                  {decision?.model_name || "robust_recency_trend_baseline"}
                </strong>
              </span>
              <span>Provenance: FORECAST</span>
            </div>
          </div>

          <div className="panel feasibility-panel">
            <div className="panel-header">
              <div>
                <div className="panel-kicker">PHYSICAL FEASIBILITY</div>
                <h2>Vessel & port checks</h2>
              </div>
              <span className="tag success">FEASIBLE</span>
            </div>

            <div className="check-list">
              <div><span>✓</span> Cargo capacity requirement</div>
              <div><span>✓</span> Dry bulk / coal compatibility</div>
              <div><span>✓</span> Vessel dimensions</div>
              <div><span>✓</span> Port draft / LOA constraints</div>
              <div><span>✓</span> Loading & discharge capability</div>
              <div><span>✓</span> Delivery window</div>
            </div>

            <div className="simulation-note">
              Test scenario data is explicitly marked SIMULATED and is not
              operational market truth.
            </div>
          </div>
        </section>

        <section className="panel recommendation-panel">
          <div className="panel-header">
            <div>
              <div className="panel-kicker">AI RECOMMENDATION</div>
              <h2>
                {recommendation === "CHARTER_NOW"
                  ? "Charter now"
                  : recommendation.replaceAll("_", " ")}
              </h2>
            </div>
            <div className="recommendation-badge">
              {recommendation.replaceAll("_", " ")}
            </div>
          </div>

          <div className="recommendation-body">
            <div className="rationale">
              {(decision?.rationale || [
                "Forecast P50 is $32.1478 USD/MT.",
                "Forecast P90 is $34.2078 USD/MT.",
                "Modeled conservative WAIT cost is higher than expected NOW cost.",
                "The current result is preliminary and freight-focused."
              ]).map((item, index) => (
                <div className="rationale-item" key={index}>
                  <span>{index + 1}</span>
                  <p>{item}</p>
                </div>
              ))}
            </div>

            <div className="decision-actions">
              <div className="action-title">HUMAN DECISION</div>

              <button
                className="action approve"
                disabled={humanLoading || !decision}
                onClick={() => submitHumanDecision("APPROVE")}
              >
                APPROVE
              </button>

              <button
                className="action modify"
                disabled={humanLoading || !decision}
                onClick={() => submitHumanDecision("MODIFY")}
              >
                MODIFY
              </button>

              <button
                className="action reject"
                disabled={humanLoading || !decision}
                onClick={() => submitHumanDecision("REJECT")}
              >
                REJECT
              </button>

              {humanDecision && (
                <div className="human-confirmation">
                  ✓ {humanDecision.action} recorded
                  <br />
                  <small>{humanDecision.id}</small>
                </div>
              )}
            </div>
          </div>
        </section>

        <footer className="footer">
          <span>CHARTERPULSE AI · SIH26006</span>
          <span>
            Decision provenance: forecast-derived · Human actions:
            USER_PROVIDED
          </span>
        </footer>
      </main>
    </div>
  );
}

export default App;
