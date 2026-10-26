import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createCargo, listPorts } from "../src/api";
import { isEvidenceBackedForecast, selectVerifiedRouteForecast, type ForecastCandidate } from "../src/utils/forecastEligibility";
import {
  isUuid,
  isValidUnlocode,
  normalizeCargoType,
  normalizeCountryCode,
  validateProcurementInput,
  vesselClassFromCargoType,
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
const procurementSource = readFileSync(
  new URL("../src/pages/NewProcurement.tsx", import.meta.url),
  "utf8",
);

test("New Procurement persists the selected vessel class separately from cargo type", () => {
  assert.match(
    procurementSource,
    /vessel_class:\s*vesselClassFromCargoType\(cargoType\)/,
  );
});

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
  assert.match(source, /validateProcurementInput\(/);
  assert.doesNotMatch(source, /Number\.isInteger\(parsedQuantity\)/);
  assert.match(source, /value=\{priority\}/);
  assert.match(source, /setPriority\(e\.target\.value\)/);
  assert.doesNotMatch(
    source,
    /onChange=\{\(e\) => setQuantity\(e\.target\.value\)\}[^]*<option value="LOW">/,
  );
  assert.match(source, /originPorts[^]*filter\([\s\S]*?isUuid\(port\.location_id\)/);
  assert.match(source, /destinationPorts[^]*filter\([\s\S]*?isUuid\(port\.location_id\)/);
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

test("UN/LOCODE validator rejects incomplete and malformed location references", () => {
  assert.equal(isValidUnlocode("AUABP"), true);
  assert.equal(isValidUnlocode("auabp"), true);
  assert.equal(isValidUnlocode("AU"), false);
  assert.equal(isValidUnlocode("AUABP-extra"), false);
  assert.equal(isValidUnlocode(null), false);
});

test("port selectors reject malformed UN/LOCODEs even when a location UUID exists", () => {
  const source = readFileSync(new URL("../src/pages/NewProcurement.tsx", import.meta.url), "utf8");
  assert.match(source, /isUuid\(port\.location_id\)\s*&&\s*isValidUnlocode\(port\.unlocode\)/);
  assert.match(source, /String\(port\.unlocode \?\? ""\)\.trim\(\)\.toUpperCase\(\)\.startsWith\(originCountry\)/);
  assert.match(source, /String\(port\.unlocode \?\? ""\)\.trim\(\)\.toUpperCase\(\)\.startsWith\(destinationCountry\)/);
});

test("location fallback does not cache empty or failed responses forever", () => {
  const source = readFileSync(new URL("../src/api.ts", import.meta.url), "utf8");
  assert.match(source, /if \(!locations\.length\) locationFallbackPromise = null/);
  assert.match(source, /\.catch\(\(\) => \{\s*\/\/ A transient outage must not poison the cache for the rest of the session\.\s*locationFallbackPromise = null;\s*return \[\];/);
});

test("country selector deduplicates country codes and normalizes case", () => {
  const source = readFileSync(new URL("../src/pages/NewProcurement.tsx", import.meta.url), "utf8");
  assert.match(source, /normalizeCountryCode\(country\.iso2, country\.country_code, country\.code\)/);
  assert.match(source, /const unique = new Map<string, Option>\(\)/);
  assert.match(source, /if \(!countryCode \|\| unique\.has\(countryCode\)\) continue/);
});


test("vessel-class selection covers every listed bulk class", () => {
  assert.equal(vesselClassFromCargoType("DRY_BULK_PANAMAX"), "Panamax");
  assert.equal(vesselClassFromCargoType("DRY_BULK_CAPESIZE"), "Capesize");
  assert.equal(vesselClassFromCargoType("DRY_BULK_HANDYSIZE"), "Handysize");
  assert.equal(vesselClassFromCargoType("DRY_BULK"), null);
  assert.equal(vesselClassFromCargoType("UNKNOWN"), null);
});

test("cargo type mapping is case-insensitive and does not misclassify ordinary cargo types", () => {
  assert.equal(vesselClassFromCargoType("dry_bulk_panamax"), "Panamax");
  assert.equal(vesselClassFromCargoType(" DRY_BULK_CAPESIZE "), "Capesize");
  assert.equal(normalizeCargoType("dry_bulk_panamax"), "DRY_BULK");
  assert.equal(normalizeCargoType(" DRY_BULK "), "DRY_BULK");
  assert.equal(normalizeCargoType("general cargo"), "general cargo");
  assert.equal(normalizeCargoType("dry_bulker"), "dry_bulker");
});

test("country normalization skips blank or invalid earlier fields", () => {
  assert.equal(normalizeCountryCode("", "au", "AUS"), "AU");
  assert.equal(normalizeCountryCode("Australia", "IN"), "IN");
  assert.equal(normalizeCountryCode("GB"), "GB");
  assert.equal(normalizeCountryCode("AUS"), "");
});

test("procurement accepts trimmed custom materials and case-insensitive location codes", () => {
  assert.equal(
    validate({
      material: "  Zinc Concentrate  ",
      originCountry: "au",
      destinationCountry: "in",
      originPortUnlocode: "auabc",
      destinationPortUnlocode: "inxyz",
    }),
    null,
  );
});

test("procurement validator rejects missing delivery dates and invalid current date", () => {
  assert.equal(validate({ fromDate: "" }), "Enter valid start and end dates.");
  assert.equal(validate({ toDate: "" }), "Enter valid start and end dates.");
  assert.match(
    validate({ today: "" }) ?? "",
    /Unable to validate the delivery window/,
  );
});


test("procurement validator rejects whitespace country codes", () => {
  assert.equal(
    validate({ originCountry: "   " }),
    "Select both origin and destination countries.",
  );
});

test("procurement validator rejects routes with duplicate UN/LOCODEs", () => {
  assert.equal(
    validate({ destinationCountry: "AU", destinationPortUnlocode: "AUABC" }),
    "Origin and destination must be different locations.",
  );
});

test("port loader filters primary API records by valid IDs and UN/LOCODE", () => {
  const source = readFileSync(new URL("../src/api.ts", import.meta.url), "utf8");
  assert.match(source, /const validPrimary = primary\s*\.filter\(p => isUuid\(p\.location_id\)\)/);
  assert.match(source, /\.filter\(p => isValidUnlocode\(unlocodeFromRecord/);
  assert.match(source, /import \{ isUuid, isValidUnlocode, normalizeCountryCode \} from "\.\/utils\/procurementValidation"/);
});

test("location fallback preserves canonical source location identifiers", () => {
  const source = readFileSync(new URL("../src/api.ts", import.meta.url), "utf8");
  assert.match(
    source,
    /return \{ \.\.\.raw, id: location\.id, name: location\.name, location_id: location\.id/,
  );
});



test("cargo API preserves varied quantities, custom materials, dates, and every priority", async () => {
  const originalFetch = globalThis.fetch;
  const bodies: Array<Record<string, unknown>> = [];
  globalThis.fetch = (async (_input: RequestInfo | URL, init?: RequestInit) => {
    bodies.push(JSON.parse(String(init?.body)) as Record<string, unknown>);
    return new Response(JSON.stringify({ id: "created" }), {
      status: 201,
      headers: { "Content-Type": "application/json" },
    });
  }) as typeof fetch;

  try {
    const cases = [
      { quantity_mt: 0.125, material: "Zinc Concentrate", priority: "LOW", vessel_class: "Handysize" },
      { quantity_mt: 70000, material: "Coking Coal", priority: "NORMAL", vessel_class: "Panamax" },
      { quantity_mt: 123456789.75, material: "Iron Ore", priority: "HIGH", vessel_class: "Capesize" },
      { quantity_mt: 1, material: "Limestone", priority: "CRITICAL", vessel_class: null },
    ];

    for (const item of cases) {
      await createCargo({
        cargo_type: "DRY_BULK",
        vessel_class: item.vessel_class,
        material: item.material,
        quantity_mt: item.quantity_mt,
        origin_location_id: "00000000-0000-4000-8000-000000000001",
        destination_location_id: "00000000-0000-4000-8000-000000000002",
        earliest_delivery: "2026-10-25T00:00:00",
        latest_delivery: "2026-11-15T23:59:59",
        priority: item.priority,
      });
    }

    assert.equal(bodies.length, 4);
    for (let i = 0; i < cases.length; i += 1) {
      assert.equal(bodies[i].quantity_mt, cases[i].quantity_mt);
      assert.equal(bodies[i].material, cases[i].material);
      assert.equal(bodies[i].vessel_class, cases[i].vessel_class);
      assert.equal(bodies[i].priority, cases[i].priority);
      assert.equal(bodies[i].origin_location_id, "00000000-0000-4000-8000-000000000001");
      assert.equal(bodies[i].destination_location_id, "00000000-0000-4000-8000-000000000002");
      assert.equal(bodies[i].earliest_delivery, "2026-10-25T00:00:00");
      assert.equal(bodies[i].latest_delivery, "2026-11-15T23:59:59");
      assert.equal(bodies[i].provenance, "USER_PROVIDED");
      assert.equal(bodies[i].source_reference, "NEW_PROCUREMENT");
    }
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("port loader retries the location fallback after an empty reference response", async () => {
  const originalFetch = globalThis.fetch;
  let locationCalls = 0;
  globalThis.fetch = (async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/api/v1/ports?")) {
      return new Response(JSON.stringify({
        count: 1,
        data: [{
          id: "00000000-0000-4000-8000-000000000010",
          location_id: "ref-au-port",
          name: "Invalid primary port",
          unlocode: "AUXXX",
        }],
      }), { status: 200, headers: { "Content-Type": "application/json" } });
    }
    if (url.includes("/api/v1/locations")) {
      locationCalls += 1;
      const data = locationCalls === 1 ? [] : [{
        id: "00000000-0000-4000-8000-000000000001",
        location_id: "ref-should-not-overwrite-canonical-id",
        name: "Abbot Point",
        country_code: "AU",
        unlocode: "AUABP",
        function: "1",
      }];
      return new Response(JSON.stringify({ count: data.length, data }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    throw new Error("Unexpected API request: " + url);
  }) as typeof fetch;

  try {
    const first = await listPorts("AU");
    assert.ok(first.every(port => !isUuid(port.location_id)));

    const second = await listPorts("AU");
    assert.equal(locationCalls, 2);
    assert.equal(second.length, 1);
    assert.equal(second[0].name, "Abbot Point");
    assert.equal(second[0].location_id, "00000000-0000-4000-8000-000000000001");
    assert.equal(second[0].id, "00000000-0000-4000-8000-000000000001");
    assert.equal(second[0].unlocode, "AUABP");
  } finally {
    globalThis.fetch = originalFetch;
  }
});


test("port loader keeps only valid live ports matching the selected country", async () => {
  const originalFetch = globalThis.fetch;
  let locationCalls = 0;
  globalThis.fetch = (async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/api/v1/ports?")) {
      return new Response(JSON.stringify({
        count: 3,
        data: [
          {
            id: "00000000-0000-4000-8000-000000000010",
            location_id: "00000000-0000-4000-8000-000000000001",
            name: "Abbot Point",
            country_code: "AU",
            unlocode: "AUABP",
          },
          {
            id: "00000000-0000-4000-8000-000000000011",
            location_id: "00000000-0000-4000-8000-000000000002",
            name: "India port",
            country_code: "IN",
            unlocode: "INXYZ",
          },
          {
            id: "00000000-0000-4000-8000-000000000012",
            location_id: "00000000-0000-4000-8000-000000000003",
            name: "Malformed port",
            country_code: "AU",
            unlocode: "AUABP-extra",
          },
        ],
      }), { status: 200, headers: { "Content-Type": "application/json" } });
    }
    if (url.includes("/api/v1/locations")) {
      locationCalls += 1;
      return new Response(JSON.stringify({ count: 0, data: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    throw new Error("Unexpected API request: " + url);
  }) as typeof fetch;

  try {
    const ports = await listPorts("AU");
    assert.equal(ports.length, 1);
    assert.equal(ports[0].name, "Abbot Point");
    assert.equal(ports[0].unlocode, "AUABP");
    assert.equal(locationCalls, 0);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("location fallback recovers after a transient network failure", async () => {
  // Load an isolated module instance so this test owns a fresh fallback cache.
  const isolatedApi = await import("../src/api.ts?transient-network-recovery-test");
  const isolatedListPorts = isolatedApi.listPorts;
  const originalFetch = globalThis.fetch;
  let locationCalls = 0;
  globalThis.fetch = (async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/api/v1/ports?")) {
      return new Response(JSON.stringify({
        count: 1,
        data: [{
          id: "00000000-0000-4000-8000-000000000010",
          location_id: "ref-au-port",
          name: "Invalid primary port",
          unlocode: "AUXXX",
        }],
      }), { status: 200, headers: { "Content-Type": "application/json" } });
    }
    if (url.includes("/api/v1/locations")) {
      locationCalls += 1;
      if (locationCalls <= 3) throw new Error("simulated temporary outage");
      const data = [{
        id: "00000000-0000-4000-8000-000000000001",
        name: "Abbot Point",
        country_code: "AU",
        unlocode: "AUABP",
        function: "1",
      }];
      return new Response(JSON.stringify({ count: 1, data }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    throw new Error("Unexpected API request: " + url);
  }) as typeof fetch;

  try {
    const first = await isolatedListPorts("AU");
    assert.ok(first.every(port => !isUuid(port.location_id)));

    const second = await isolatedListPorts("AU");
    assert.equal(locationCalls, 4);
    assert.equal(second.length, 1);
    assert.equal(second[0].location_id, "00000000-0000-4000-8000-000000000001");
  } finally {
    globalThis.fetch = originalFetch;
  }
});


test("quantity validation rejects non-decimal Number coercion formats", () => {
  for (const quantity of ["0x10", "0b10", "0o10", "Infinity", "NaN", "1e309", "1_000"]) {
    assert.notEqual(
      validate({ quantity }),
      null,
      "quantity " + JSON.stringify(quantity) + " should be rejected",
    );
  }
});

test("quantity validation accepts decimal and scientific notation boundaries", () => {
  for (const quantity of ["0.0000001", ".125", "1.", "1e3", "1E+3", " 12.5 "]) {
    assert.equal(
      validate({ quantity }),
      null,
      "quantity " + JSON.stringify(quantity) + " should be accepted",
    );
  }
  for (const quantity of ["0", "-0.1", "1e-9999"]) {
    assert.notEqual(validate({ quantity }), null);
  }
});

test("date validation rejects unsupported year zero and malformed date shapes", () => {
  for (const date of ["0000-01-01", "26-10-25", "2026/10/25", "2026-1-5", "2026-02-29"]) {
    assert.notEqual(
      validate({ fromDate: date }),
      null,
      "date " + JSON.stringify(date) + " should be rejected",
    );
  }
});

test("deterministic mutation sweep preserves quantity validation invariants", () => {
  const validQuantities = ["0.0001", "0.1", "1", "25", "70000", "1000000000.75", "2.5e4"];
  const invalidQuantities = ["", " ", "0", "-1", "-0.0001", "abc", "0x20", "Infinity", "1e999"];
  for (const quantity of validQuantities) {
    assert.equal(validate({ quantity }), null, "expected valid quantity " + quantity);
  }
  for (const quantity of invalidQuantities) {
    assert.notEqual(validate({ quantity }), null, "expected invalid quantity " + quantity);
  }
});


const forecastOrigin = "00000000-0000-4000-8000-000000000001";
const forecastDestination = "00000000-0000-4000-8000-000000000002";

function validEvidenceForecast(overrides: Partial<ForecastCandidate> = {}): ForecastCandidate {
  return {
    id: "forecast-evidence-valid",
    origin_location_id: forecastOrigin,
    destination_location_id: forecastDestination,
    vessel_class: "Panamax",
    p10: 28,
    p50: 31,
    p90: 35,
    unit: "USD/MT",
    provenance: "FORECAST",
    generated_at: "2026-10-26T10:00:00Z",
    metadata: {
      route_scoped: true,
      input_provenance: "MARKET_OBSERVATION",
      observation_count: 12,
      distinct_observation_dates: 12,
      source_provenances: ["REAL"],
    },
    ...overrides,
  };
}

test("forecast eligibility rejects legacy static, simulated, unscoped, and malformed forecasts", () => {
  assert.equal(isEvidenceBackedForecast(validEvidenceForecast()), true);
  assert.equal(isEvidenceBackedForecast(validEvidenceForecast({ provenance: "PUBLIC_PROXY_REFERENCE" })), false);
  assert.equal(isEvidenceBackedForecast(validEvidenceForecast({ provenance: "SIMULATED" })), false);
  assert.equal(isEvidenceBackedForecast(validEvidenceForecast({ unit: "USD_per_40ft_container" })), false);
  assert.equal(isEvidenceBackedForecast(validEvidenceForecast({ p10: Number.NaN })), false);
  assert.equal(isEvidenceBackedForecast(validEvidenceForecast({ p10: 32, p50: 31, p90: 35 })), false);
  assert.equal(isEvidenceBackedForecast(validEvidenceForecast({
    metadata: {
      route_scoped: true,
      input_provenance: "MARKET_OBSERVATION",
      observation_count: 2,
      distinct_observation_dates: 2,
      source_provenances: ["REAL"],
    },
  })), false);
  assert.equal(isEvidenceBackedForecast(validEvidenceForecast({
    metadata: {
      route_scoped: true,
      input_provenance: "MARKET_OBSERVATION",
      observation_count: 12,
      distinct_observation_dates: 12,
      source_provenances: ["SIMULATED"],
    },
  })), false);
});

test("forecast selector requires exact route and vessel class; it does not wildcard missing class", () => {
  const valid = validEvidenceForecast({ id: "valid-older", generated_at: "2026-10-25T10:00:00Z" });
  const newerSameRoute = validEvidenceForecast({ id: "valid-newer", generated_at: "2026-10-26T12:00:00Z" });
  const wrongRoute = validEvidenceForecast({
    id: "wrong-route",
    origin_location_id: "00000000-0000-4000-8000-000000000003",
    generated_at: "2026-10-26T15:00:00Z",
  });
  const wrongClass = validEvidenceForecast({ id: "wrong-class", vessel_class: "Capesize", generated_at: "2026-10-27T10:00:00Z" });
  const legacyStatic = validEvidenceForecast({ id: "legacy-static", provenance: "PUBLIC_PROXY_REFERENCE", generated_at: "2026-10-28T10:00:00Z" });

  const selected = selectVerifiedRouteForecast(
    [valid, wrongRoute, wrongClass, legacyStatic, newerSameRoute],
    {
      originLocationId: forecastOrigin,
      destinationLocationId: forecastDestination,
      vesselClass: "PANAMAX",
    },
  );
  assert.equal(selected?.id, "valid-newer");
  assert.equal(selectVerifiedRouteForecast([valid], {
    originLocationId: forecastOrigin,
    destinationLocationId: forecastDestination,
    vesselClass: null,
  }), null);
  assert.equal(selectVerifiedRouteForecast([valid] as never[], {
    originLocationId: forecastOrigin,
    destinationLocationId: forecastOrigin,
    vesselClass: "Panamax",
  }), null);
});

test("market API observations are not silently merged with local static reference rows", () => {
  assert.doesNotMatch(apiSource, /REFERENCE_MARKET_OBSERVATIONS/);
  assert.match(apiSource, /export async function listMarketObservations\(\): Promise<MarketObservation\[]> \{\s*\/\/ Only return API observations/);
});

test("decision API requires explicit saved cargo and forecast identifiers", () => {
  assert.doesNotMatch(apiSource, /TEST_CARGO_ID|TEST_FORECAST_ID/);
  assert.match(
    apiSource,
    /evaluateDecision\(cargoQuantityMt: number, waitDays: number, cargoRequirementId: string, forecastId: string\)/,
  );
});

test("Decision Room uses evidence-checked route forecast selection", () => {
  assert.match(appSource, /selectVerifiedRouteForecast/);
  assert.doesNotMatch(appSource, /function selectRouteForecast\(/);
});
