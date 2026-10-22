import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

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
