# CHARTERPULSE AI --- Requirements Traceability

## Functional requirements

### R1 Freight forecast

Historical market data -\> future freight estimates. Implementation:
`ml/forecasting`, forecast API.

### R2 Market entry timing

Recommend book-now/wait/review using forecast, constraints and delivery
window. Implementation: decision engine + optimization.

### R3 Vessel optimization

Recommend feasible vessel class for cargo and route. Implementation:
vessel intelligence + compatibility + optimization.

### R4 Port constraints

Account for draft, LOA, beam, terminal and handling limitations.
Implementation: port database + feasibility engine.

### R5 Risk mitigation

Identify volatility, congestion, weather and delay risk. Implementation:
`risk/`.

### R6 Dashboard

User enters cargo, route and contract information and receives analysis.
Implementation: `apps/web/`.

### R7 Contract strategy

Compare spot and short/medium-term approaches where assumptions/data
support it. Implementation: procurement + optimization.

### R8 Explainability

Show why the recommendation was produced. Implementation: decision
engine + forecast/risk metadata.

### R9 Human decision

Store approve/modify/reject. Implementation: decisions.

### R10 Actual outcome

Store what happened. Implementation: outcomes.

### R11 Model evaluation

Compare predictions and decisions against actuals and baselines.
Implementation: `ml/evaluation`.

## Explicitly out of first-release scope

Full airline optimization, trucking marketplace, railway optimization,
3D globe, autonomous charter execution, perfect prediction and a generic
AI chatbot as the primary feature.

Every additional feature must map to a SIH requirement, a user decision
or a measurable technical output.
