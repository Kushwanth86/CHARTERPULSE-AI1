const API_BASE = "http://127.0.0.1:8000";

export const TEST_CARGO_ID =
  "ca16e396-bacf-49b3-a06f-c4b9373dd26b";

export const TEST_FORECAST_ID =
  "6e7e8284-9b73-49b1-9767-30f536a7911a";

export interface DecisionResponse {
  decision_run_id: string | null;
  decision_status: string;
  recommendation: string;
  cargo_quantity_mt: number;
  currency: string;
  forecast_p10: number;
  forecast_p50: number;
  forecast_p90: number;
  now_expected_freight_cost: number;
  now_p90_freight_cost: number;
  wait_conservative_rate: number;
  wait_conservative_cost: number;
  wait_cost_difference: number;
  wait_cost_difference_per_mt: number;
  probability_now_exceeds_baseline: number;
  risk_score: number;
  provenance: string;
  model_name: string | null;
  forecast_id: string;
  rationale: string[];
  warnings: string[];
  generated_at: string;
}

export interface HumanDecisionResponse {
  id: string;
  decision_run_id: string;
  action: string;
  modified_parameters: Record<string, unknown>;
  reason: string | null;
  decided_at: string;
  actor_reference: string | null;
  provenance: string;
}

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {})
    },
    ...options
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(
      `API ${response.status}: ${text || response.statusText}`
    );
  }

  return response.json();
}

export async function evaluateDecision(
  cargoQuantityMt: number,
  waitDays: number
): Promise<DecisionResponse> {
  return request<DecisionResponse>("/api/v1/decision/evaluate", {
    method: "POST",
    body: JSON.stringify({
      forecast_id: TEST_FORECAST_ID,
      cargo_requirement_id: TEST_CARGO_ID,
      cargo_quantity_mt: cargoQuantityMt,
      wait_days: waitDays,
      simulations: 5000,
      seed: 42,
      currency: "USD"
    })
  });
}

export async function recordHumanDecision(
  decisionRunId: string,
  action: "APPROVE" | "MODIFY" | "REJECT",
  reason: string
): Promise<HumanDecisionResponse> {
  return request<HumanDecisionResponse>("/api/v1/decisions/human", {
    method: "POST",
    body: JSON.stringify({
      decision_run_id: decisionRunId,
      action,
      modified_parameters: {},
      reason,
      actor_reference: "CHARTERPULSE_WEB_USER"
    })
  });
}
