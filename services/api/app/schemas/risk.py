from pydantic import BaseModel, Field


class RiskSimulationRequest(BaseModel):
    p10: float = Field(ge=0)
    p50: float = Field(ge=0)
    p90: float = Field(ge=0)
    cargo_quantity_mt: float = Field(gt=0)
    baseline_rate: float = Field(ge=0)
    simulations: int = Field(default=5000, ge=100, le=100000)
    seed: int = Field(default=42)


class RiskSimulationResponse(BaseModel):
    scenario: str
    simulations: int
    expected_rate_per_mt: float
    p10_rate_per_mt: float
    p50_rate_per_mt: float
    p90_rate_per_mt: float
    expected_cost: float
    p90_cost: float
    probability_cost_above_baseline: float
    risk_score: float
    provenance: str
