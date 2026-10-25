import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import type { FreightForecast, Vessel } from "../src/api";
import { selectRecommendedVessel, vesselCapacityMt } from "../src/utils/vesselSelection";
import { selectRouteForecast } from "../src/utils/forecastSelection";

const apiSource = readFileSync(
  new URL("../src/api.ts", import.meta.url),
  "utf8",
);
const appSource = readFileSync(
  new URL("../src/App.tsx", import.meta.url),
  "utf8",
);

test("port loader enforces the selected country after primary API responses", () => {
  assert.match(
    apiSource,
    /const validPrimary = primary[\s\S]*\.filter\(p => \{[\s\S]*countryCodeFromRecord\(raw\) === normalized[\s\S]*unlocodeFromRecord\(raw\)\.slice\(0, 2\) === normalized/,
  );
});

test("MODIFY human decisions accept and send explicit modified parameters", () => {
  assert.match(
    apiSource,
    /export async function recordHumanDecision\([\s\S]*modifiedParameters: Record<string, unknown> = \{\}/,
  );
  assert.match(apiSource, /modified_parameters: modifiedParameters/);
});

test("Decision Room renders delivery dates as date-only values", () => {
  assert.match(appSource, /function formatDateOnly\(value\?: string \| null\)/);
  assert.match(
    appSource,
    /formatDateOnly\(procurement\.cargo\.earliest_delivery\)/,
  );
  assert.match(
    appSource,
    /formatDateOnly\(procurement\.cargo\.latest_delivery\)/,
  );
  assert.doesNotMatch(
    appSource,
    /new Date\(procurement\.cargo\.earliest_delivery/,
  );
});

test("frontend API base is not a localhost-only production endpoint", () => {
  assert.doesNotMatch(apiSource, /127\.0\.0\.1:8000/);
  assert.match(apiSource, /https:\/\/charterpulse-ai1\.onrender\.com/);
});

test("procurement intake preserves invalid quantity input and validates before submission", () => {
  const source = readFileSync(
    new URL("../src/pages/NewProcurement.tsx", import.meta.url),
    "utf8",
  );
  assert.match(source, /setQuantity\(e\.target\.value\)/);
  assert.match(source, /Number\.isInteger\(parsedQuantity\)/);
  assert.match(source, /parsedQuantity <= 0/);
  assert.match(source, /defaultDeliveryWindow/);
  assert.doesNotMatch(source, /setQuantity\(Math\.max\(1,/);
});

test("human decision controls guard duplicate submissions and report save status", () => {
  assert.match(appSource, /submittingAction/);
  assert.match(appSource, /disabled=\{busy \|\| Boolean\(submittingAction\)/);
  assert.match(appSource, /Decision \$\{saved\.action\.toLowerCase\(\)\} was saved successfully\./);
  assert.match(appSource, /The save was not confirmed\./);
});

test("human decision history reads persisted records from the API", () => {
  const historySource = readFileSync(
    new URL("../src/pages/DecisionHistory.tsx", import.meta.url),
    "utf8",
  );
  const routeSource = readFileSync(
    new URL("../../../services/api/app/api/routes/human_decision.py", import.meta.url),
    "utf8",
  );
  const serviceSource = readFileSync(
    new URL("../../../services/api/app/services/human_decision_service.py", import.meta.url),
    "utf8",
  );

  assert.match(apiSource, /export async function listHumanDecisions/);
  assert.match(apiSource, /\/api\/v1\/decisions\/human/);
  assert.match(historySource, /listHumanDecisions\(\)/);
  assert.match(historySource, /Saved human decisions are loaded from the server/);
  assert.match(routeSource, /@router\.get\([\s\S]*\/human/);
  assert.match(serviceSource, /\.table\("human_decisions"\)[\s\S]*\.order\("decided_at", desc=True\)/);
});


function makeVessel(
  overrides: Partial<Vessel> & Pick<Vessel, "id" | "name" | "provenance">,
): Vessel {
  return {
    vessel_class: "Bulk Carrier",
    cargo_capacity_mt: null,
    dwt: null,
    dwt_mt: null,
    ...overrides,
  };
}

test("recommendation uses dwt_mt when cargo capacity is not populated", () => {
  const smaller = makeVessel({
    id: "small",
    name: "SMALL BULKER",
    provenance: "PUBLIC_PROXY",
    dwt_mt: 60000,
  });
  const suitable = makeVessel({
    id: "suitable",
    name: "OCEAN EMERALD",
    provenance: "PUBLIC_PROXY",
    dwt_mt: 92950,
  });

  assert.equal(
    selectRecommendedVessel([smaller, suitable], 70000),
    suitable,
  );
  assert.equal(vesselCapacityMt(suitable), 92950);
});

test("recommendation chooses the smallest suitable vessel by available capacity", () => {
  const larger = makeVessel({
    id: "larger",
    name: "LARGE BULKER",
    provenance: "PUBLIC_PROXY",
    dwt_mt: 120000,
  });
  const smallerSuitable = makeVessel({
    id: "smaller-suitable",
    name: "MEDIUM BULKER",
    provenance: "PUBLIC_PROXY",
    dwt_mt: 80000,
  });

  assert.equal(
    selectRecommendedVessel([larger, smallerSuitable], 70000),
    smallerSuitable,
  );
});

test("populated cargo capacity takes precedence over deadweight", () => {
  const knownCapacity = makeVessel({
    id: "capacity-known",
    name: "CAPACITY-KNOWN BULKER",
    provenance: "PUBLIC_PROXY",
    cargo_capacity_mt: 65000,
    dwt_mt: 100000,
  });

  assert.equal(vesselCapacityMt(knownCapacity), 65000);
  assert.notEqual(
    selectRecommendedVessel([knownCapacity], 70000),
    knownCapacity,
  );
});


function makeForecast(
  overrides: Partial<FreightForecast> & Pick<FreightForecast, "id">,
): FreightForecast {
  return {
    origin_location_id: "AUABP-ID",
    destination_location_id: "INACH-ID",
    vessel_class: "Panamax",
    p10: 27,
    p50: 30,
    p90: 34,
    baseline: 30,
    provenance: "VERIFIED",
    generated_at: "2026-10-24T10:00:00Z",
    ...overrides,
  };
}

test("route forecast selection excludes unrelated routes and matches vessel class case-insensitively", () => {
  const olderMatching = makeForecast({
    id: "matching-old",
    generated_at: "2026-10-24T10:00:00Z",
    vessel_class: "PANAMAX",
  });
  const newerMatching = makeForecast({
    id: "matching-new",
    generated_at: "2026-10-25T10:00:00Z",
    vessel_class: "Panamax",
  });
  const unrelatedRoute = makeForecast({
    id: "other-route",
    origin_location_id: "OTHER-ORIGIN",
    generated_at: "2026-10-26T10:00:00Z",
  });
  const wrongVesselClass = makeForecast({
    id: "wrong-class",
    vessel_class: "Capesize",
    generated_at: "2026-10-27T10:00:00Z",
  });

  assert.equal(
    selectRouteForecast(
      [olderMatching, newerMatching, unrelatedRoute, wrongVesselClass],
      "AUABP-ID",
      "INACH-ID",
      "panamax",
    ),
    newerMatching,
  );
});

test("route forecast selection returns null when exact route identifiers are unavailable", () => {
  const unrelatedRoute = makeForecast({
    id: "other-route",
    origin_location_id: "OTHER-ORIGIN",
  });

  assert.equal(
    selectRouteForecast([unrelatedRoute], "AUABP-ID", "INACH-ID", "Panamax"),
    null,
  );
  assert.equal(
    selectRouteForecast([unrelatedRoute], undefined, "INACH-ID", "Panamax"),
    null,
  );
});
