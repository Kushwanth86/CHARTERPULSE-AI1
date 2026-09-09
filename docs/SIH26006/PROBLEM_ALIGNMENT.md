# CHARTERPULSE AI --- SIH26006 Problem Alignment

## Problem fit

SIH26006 asks for an intelligent freight forecasting model for optimized
vessel chartering and bulk cargo procurement from overseas to India's
East Coast. The statement highlights reactive market exploration,
freight volatility, vessel-type selection, port infrastructure
constraints, idle time, congestion and risk, and asks for a
user-friendly dashboard with actionable recommendations.

## Mapping

  SIH Need                      Module
  ----------------------------- --------------------------------------
  Freight forecasting           `ml/forecasting`
  Historical freight analysis   `ml/data` + data connectors
  Market entry timing           decision engine + optimization
  Vessel type optimization      feasibility + optimization
  Port constraints              port intelligence + feasibility
  Idle scenario support         optimization/risk
  Congestion warning            port data + risk
  Dashboard                     `apps/web`
  Short/medium-term strategy    procurement + optimization
  Risk mitigation               `risk`
  Actionable recommendation     decision engine
  Outcome evaluation            decisions + outcomes + ML evaluation

## Scope

The first working system must prove the maritime bulk
procurement/chartering use case for East Coast India. Global port
architecture is an extensibility layer, not permission to build an
unrelated global transport platform.
