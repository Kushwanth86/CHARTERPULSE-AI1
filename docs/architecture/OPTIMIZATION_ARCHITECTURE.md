# CHARTERPULSE AI — Optimization Architecture

## 1. Purpose

The optimization layer converts cargo, vessel, route, timing, cost, and risk information into feasible transportation and chartering strategies.

The objective is not simply to minimize ocean freight. The system should minimize expected total delivered cost while respecting physical, operational, contractual, inventory, and risk constraints.

## 2. Optimization Flow

```text
Cargo Requirement
      ↓
Candidate Ports / Vessels / Routes
      ↓
Physical Feasibility Gate
      ↓
Cost Components
      ↓
Forecast + Uncertainty
      ↓
Risk Scenarios
      ↓
Optimization Model
      ↓
Feasible Strategies
      ↓
Ranked Alternatives
      ↓
Decision Engine
```

## 3. Decision Variables

Depending on the scenario, variables may include:

- selected vessel or vessel class
- number of vessels
- charter timing
- charter type/contract strategy
- cargo allocation
- origin port
- destination port
- route
- loading and discharge schedule
- transportation mode
- inventory timing

The model must not assume that every variable is required for every shipment.

## 4. Objective

The primary objective is total delivered cost.

A generalized objective is:

```text
Total Delivered Cost =
    Cargo Cost
  + Ocean Freight
  + Bunker/Fuel
  + Port Charges
  + Canal Charges
  + Loading/Discharge
  + Inland Logistics
  + Storage
  + Insurance
  + Demurrage / Delay
  + Idle Vessel Cost
  + Expected Risk Cost
```

Only components supported by available data should be included. Missing market observations must not be replaced with fabricated values.

## 5. Constraints

### Cargo

- required quantity
- acceptable quantity tolerance
- cargo type compatibility
- delivery requirement

### Vessel

- vessel capacity
- availability window
- vessel class
- cargo compatibility
- draft
- LOA
- beam
- operational restrictions

### Port

- port availability
- terminal capability
- berth constraints
- draft restrictions
- cargo handling capability
- loading/discharge capacity

### Time

- earliest loading
- latest loading
- transit time
- delivery deadline
- port waiting time
- vessel availability

### Commercial

- budget constraints
- charter terms
- contract constraints
- procurement constraints

### Inventory

- minimum inventory
- expected consumption
- stockout threshold
- safety stock

## 6. Feasibility Before Optimization

Optimization must not select an option that is physically impossible.

The pipeline is therefore:

```text
Candidate
  ↓
Physical Feasibility
  ↓
Operational Feasibility
  ↓
Commercial Feasibility
  ↓
Optimization
```

Examples of hard failures include an incompatible vessel, insufficient capacity, impossible draft, unavailable berth, or delivery schedule that cannot be met.

## 7. Solver Strategy

The architecture supports constrained optimization methods such as:

- MILP
- CP-SAT
- other validated mathematical programming methods

A simpler deterministic optimizer may be used for the MVP when the decision problem does not require a full solver. The solver should be selected based on the actual mathematical structure rather than technology branding.

## 8. Alternative Strategies

The engine should return multiple feasible alternatives when possible, for example:

1. Charter now — lowest expected cost
2. Wait — lower current commitment but higher uncertainty
3. Alternative vessel class
4. Alternative origin/destination port
5. Split shipment
6. Alternative charter contract

Each alternative should expose cost, timing, feasibility, and risk.

## 9. Uncertainty and Risk

Forecast ranges and risk scenarios must be incorporated into decision analysis where available.

The optimization layer may compare:

- expected cost
- P90 cost
- CVaR or other downside-risk metric
- delivery reliability
- stockout risk

A recommendation should not optimize a point estimate while ignoring material uncertainty.

## 10. What-If Analysis

The same optimization model should support scenario changes such as:

- cargo quantity change
- delivery date change
- freight shock
- fuel price change
- port congestion
- vessel unavailability
- alternative port
- budget change

Each scenario should preserve the original decision context and record its assumptions.

## 11. Optimization Output Contract

A strategy result should contain at least:

```text
strategy_id
status
selected_vessel / vessel_class
selected_origin
selected_destination
route
cargo_quantity
charter_timing
contract_type
estimated_total_cost
cost_breakdown
expected_delay
risk_metrics
feasibility_status
constraints_checked
model_version
created_at
```

## 12. Explainability

The optimization result must explain why an option won.

Examples:

- lowest expected delivered cost
- meets delivery deadline
- vessel passes physical compatibility checks
- lower downside risk than the cheapest alternative
- alternative port reduces congestion exposure

Explanations must be generated from actual model inputs and results.

## 13. Validation

Optimization tests must verify:

- infeasible options are rejected
- capacity constraints are respected
- port restrictions are respected
- delivery deadlines are respected
- cargo requirements are satisfied
- cost calculations reconcile
- solver results are reproducible under identical inputs

## 14. Integration Boundaries

Optimization consumes validated data from the platform and returns candidate strategies to the decision engine. It does not independently invent market data, vessel availability, port capability, or forecasts.
