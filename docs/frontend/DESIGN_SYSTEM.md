# CHARTERPULSE AI — Frontend Design System

## 1. Purpose

The CHARTERPULSE AI frontend is a decision-support application for maritime procurement and chartering. The interface should prioritize operational clarity, evidence, uncertainty, and decision traceability over decorative dashboards.

## 2. Design Principles

### Decision first
Users should quickly understand what decision is being evaluated and what action is recommended.

### Evidence visible
Market values, forecasts, vessel observations, port information, and derived calculations should show source/provenance and freshness where relevant.

### Uncertainty visible
Forecast ranges and risk should not be hidden behind a single number.

### Human control
Recommendations require human approval, modification, or rejection. The UI must never imply that AI has independently executed a charter.

### Consistent density
The application is an operations workspace. Tables, metrics, alerts, and comparisons should be compact enough for professional use without becoming unreadable.

## 3. Application Structure

Primary navigation:

- Command Center
- New Procurement
- Market Intelligence
- Freight Forecast
- Port Intelligence
- Vessel Intelligence
- Route & Feasibility
- Cost Optimization
- Charter Strategy
- Risk Analysis
- AI Recommendation
- Decision History
- Actual Outcomes
- Feedback & Model Performance

## 4. Visual Hierarchy

A typical decision page should follow:

```text
Context
  ↓
Key Decision
  ↓
Recommendation
  ↓
Evidence
  ↓
Alternatives
  ↓
Risk / Uncertainty
  ↓
Human Action
```

Primary actions must be visually distinct from navigation and informational controls.

## 5. Status Vocabulary

Use consistent semantic states:

- `SUCCESS` — completed/healthy/feasible
- `WARNING` — usable but requires attention
- `ERROR` — failed or unsafe
- `INFO` — informational
- `UNKNOWN` — insufficient evidence
- `STALE` — observation exists but freshness threshold has been exceeded
- `FORECAST` — predicted rather than observed
- `SIMULATED` — scenario output rather than actual market data

Do not represent uncertain data as confirmed data.

## 6. Provenance Display

When showing external or derived information, use the platform provenance vocabulary:

- REAL
- PUBLIC_PROXY
- SIMULATED
- USER_PROVIDED
- DERIVED
- FORECAST

A compact source/freshness indicator should be available beside important market and operational values.

## 7. Core Components

The design system should provide reusable components for:

- KPI cards
- metric groups
- data tables
- sortable/filterable tables
- charts
- forecast bands
- risk summaries
- status badges
- provenance badges
- freshness indicators
- recommendation cards
- alternative comparison cards
- decision action panels
- forms
- date/time selectors
- cargo selectors
- port selectors
- vessel selectors
- modal dialogs
- confirmation dialogs
- alerts
- empty states
- loading states
- error states

## 8. Tables

Tables should support:

- clear column labels
- units
- sorting where appropriate
- filtering
- pagination for large datasets
- source/freshness where relevant
- explicit empty states

Do not use color alone to communicate important status.

## 9. Charts

Charts should communicate decision-relevant information such as:

- freight history
- forecast P10/P50/P90
- cost breakdown
- scenario comparison
- risk distribution
- vessel availability timeline
- port congestion

Axes must include units and time ranges where applicable. Tooltips should expose precise values and timestamps.

## 10. Forms

Procurement forms should capture structured requirements instead of free text whenever the value has operational meaning.

Examples:

- cargo/material
- quantity
- unit
- origin country/region/port
- destination country/region/port
- delivery window
- budget
- preferred charter strategy

Validation should occur before expensive forecast or optimization requests are submitted.

## 11. Decision Workspace

The main recommendation view should expose:

```text
Recommendation
Confidence / evidence quality
Expected total delivered cost
Risk
Delivery feasibility
Best alternative
Why this recommendation

[ APPROVE ] [ MODIFY ] [ REJECT ]
```

The exact action buttons must reflect backend-supported actions and must not imply execution when the system only records a decision.

## 12. Responsive Behavior

The desktop layout is the primary operational experience. Tablet and smaller layouts should preserve the decision hierarchy and avoid hiding critical risk or feasibility information.

## 13. Accessibility

The frontend should support:

- keyboard navigation
- visible focus states
- semantic HTML
- accessible labels
- sufficient text contrast
- non-color status indicators
- readable error messages
- chart alternatives or summaries

## 14. Loading and Failure States

Every data-driven page needs explicit states for:

- loading
- empty
- stale
- partial data
- API error
- permission error
- invalid input

The UI must not replace a failed API response with fabricated market values.

## 15. Design Tokens

Centralize reusable values for:

- typography
- spacing
- border radius
- shadows
- sizing
- layout widths
- breakpoints
- semantic status states

Component-level hard-coded styling should be minimized so the interface remains consistent as modules grow.

## 16. Frontend Data Boundary

The frontend should consume typed API contracts through service modules. Business calculations should remain in backend/domain services unless the calculation is purely presentational.

The browser must never receive or store Supabase secret keys or other privileged backend credentials.

## 17. Decision Traceability

Important screens should make it possible to navigate from:

```text
Cargo Requirement
→ Forecast
→ Feasibility
→ Cost
→ Risk
→ Recommendation
→ Human Decision
→ Actual Outcome
```

This is a core product requirement, not merely a navigation preference.
