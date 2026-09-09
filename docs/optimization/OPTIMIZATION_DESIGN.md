# CHARTERPULSE AI --- Optimization Design

## Objective

Select a feasible procurement/charter strategy balancing cost, risk and
reliability.

## Decision variables

Depending on available data: - vessel class/count - shipment quantity -
charter timing - contract type - shipment schedule - origin/destination
port - route

## Constraints

Cargo quantity and delivery window; vessel capacity, draft, LOA, beam
and availability; port/terminal capability; inventory; budget and
commercial limits.

## Objective

``` text
Minimize:
Expected Delivered Cost
+ Risk Penalty
+ Delay Cost
+ Idle/Repositioning Cost
```

## Scenarios

Evaluate P10/P50/P90 freight and shocks to congestion, fuel and delay.

## Solver abstraction

Business logic calls a `SolverInterface`; the first implementation can
use an available open-source solver such as PuLP. Solver choice must
remain replaceable.

## Rule

Feasibility is a hard gate. Do not optimize an impossible vessel/port
combination.
