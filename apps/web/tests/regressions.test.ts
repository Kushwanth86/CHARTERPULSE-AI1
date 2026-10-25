import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  isUuid,
  validateProcurementInput,
  type ProcurementValidationInput,
} from "../src/utils/procurementValidation";

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

test("procurement intake supports custom materials, editable quantities, and correct priority state", () => {
  const source = readFileSync(
    new URL("../src/pages/NewProcurement.tsx", import.meta.url),
    "utf8",
  );
  assert.match(source, /id="procurement-material"/);
  assert.match(source, /list="procurement-material-options"/);
  assert.match(source, /setMaterial\(event\.target\.value\)/);
  assert.match(source, /step="any"/);
  assert.match(source, /setQuantity\(event\.target\.value\)/);
  assert.match(source, /parsedQuantity <= 0/);
  assert.doesNotMatch(source, /Number\.isInteger\(parsedQuantity\)/);
  assert.match(source, /value=\{priority\}/);
  assert.match(source, /setPriority\(e\.target\.value\)/);
  assert.doesNotMatch(
    source,
    /onChange=\{\(e\) => setQuantity\(e\.target\.value\)\}[^]*<option value="LOW">/,
  );
  assert.match(source, /originPorts[^]*filter\(\(port\) => isUuid\(port\.location_id\)\)/);
  assert.match(source, /destinationPorts[^]*filter\(\(port\) => isUuid\(port\.location_id\)\)/);
  assert.match(source, /const \[material, setMaterial\] = useState\(""\)/);
  assert.match(source, /const \[quantity, setQuantity\] = useState\(""\)/);
  assert.match(source, /defaultDeliveryWindow/);
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


const validProcurementInput: ProcurementValidationInput = {
  material: "Iron Ore",
  cargoType: "DRY_BULK_PANAMAX",
  originCountry: "AU",
  destinationCountry: "IN",
  originPortLocationId: "00000000-0000-4000-8000-000000000001",
  destinationPortLocationId: "00000000-0000-4000-8000-000000000002",
  originPortUnlocode: "AUABC",
  destinationPortUnlocode: "INXYZ",
  quantity: "12500.5",
  fromDate: "2026-10-25",
  toDate: "2026-11-15",
  today: "2026-10-25",
  priority: "NORMAL",
};

function validate(overrides: Partial<ProcurementValidationInput> = {}) {
  return validateProcurementInput({
    ...validProcurementInput,
    ...overrides,
  });
}

test("procurement validator accepts decimal MT and each supported priority", () => {
  for (const priority of ["LOW", "NORMAL", "HIGH", "CRITICAL"]) {
    assert.equal(validate({ priority, quantity: "0.125" }), null);
  }
});

test("procurement validator rejects blank and whitespace-only materials", () => {
  assert.equal(validate({ material: "" }), "Enter a material or commodity.");
  assert.equal(validate({ material: "   " }), "Enter a material or commodity.");
});

test("procurement validator rejects missing cargo type, countries, and ports", () => {
  assert.equal(validate({ cargoType: "" }), "Select a cargo type.");
  assert.equal(
    validate({ originCountry: "" }),
    "Select both origin and destination countries.",
  );
  assert.equal(
    validate({ destinationCountry: "" }),
    "Select both origin and destination countries.",
  );
  assert.equal(
    validate({ originPortLocationId: "" }),
    "Select both origin and destination ports.",
  );
  assert.equal(
    validate({ destinationPortLocationId: null }),
    "Select both origin and destination ports.",
  );
});

test("procurement validator rejects invalid IDs and malformed port codes", () => {
  assert.equal(
    validate({ originPortLocationId: "ref-au-gla" }),
    "The selected ports do not have valid live location IDs. Select ports backed by verified API location data.",
  );
  assert.equal(
    validate({ destinationPortLocationId: "not-a-uuid" }),
    "The selected ports do not have valid live location IDs. Select ports backed by verified API location data.",
  );
  assert.equal(
    validate({ originPortUnlocode: "AU" }),
    "The origin port is missing a valid UN/LOCODE.",
  );
  assert.equal(
    validate({ destinationPortUnlocode: "" }),
    "The destination port is missing a valid UN/LOCODE.",
  );
});

test("procurement validator catches ports left over from a different country selection", () => {
  assert.equal(
    validate({ originCountry: "IN" }),
    "The origin port does not belong to the selected origin country. Reselect the port.",
  );
  assert.equal(
    validate({ destinationCountry: "AU" }),
    "The destination port does not belong to the selected destination country. Reselect the port.",
  );
});

test("procurement validator rejects same-location routes", () => {
  assert.equal(
    validate({
      destinationPortLocationId: validProcurementInput.originPortLocationId,
    }),
    "Origin and destination must be different locations.",
  );
});

test("procurement validator rejects zero, negative, nonnumeric, and infinite quantities", () => {
  for (const quantity of ["", " ", "0", "-1", "NaN", "Infinity", "1e309", "abc"]) {
    assert.notEqual(validate({ quantity }), null, "quantity " + JSON.stringify(quantity) + " should be rejected");
  }
});

test("procurement validator accepts large finite quantities without coercing them", () => {
  assert.equal(validate({ quantity: "1000000000.75" }), null);
});

test("procurement validator rejects invalid calendar dates and past delivery windows", () => {
  assert.equal(
    validate({ fromDate: "2026-02-31" }),
    "Enter valid start and end dates.",
  );
  assert.equal(
    validate({ toDate: "2026-13-01" }),
    "Enter valid start and end dates.",
  );
  assert.equal(
    validate({ fromDate: "2026-10-24" }),
    "From Date cannot be in the past.",
  );
});

test("procurement validator requires an ordered inclusive date window", () => {
  assert.equal(validate({ fromDate: "2026-11-16", toDate: "2026-11-15" }), "From Date must be on or before To Date.");
  assert.equal(validate({ fromDate: "2026-10-25", toDate: "2026-10-25" }), null);
});

test("procurement validator rejects unknown priority values", () => {
  assert.equal(
    validate({ priority: "URGENT??" }),
    "Select a valid procurement priority.",
  );
});

test("UUID validator excludes synthetic reference IDs and malformed UUIDs", () => {
  assert.equal(isUuid("00000000-0000-4000-8000-000000000001"), true);
  assert.equal(isUuid("ref-au-gla"), false);
  assert.equal(isUuid("00000000-0000-0000-0000-000000000001"), false);
  assert.equal(isUuid(null), false);
});
