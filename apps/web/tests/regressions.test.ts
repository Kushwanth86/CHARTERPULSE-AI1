import test from "node:test";
import assert from "node:assert/strict";

import { filterPortsByCountry } from "../src/utils/portFiltering.ts";
import { formatDateOnly } from "../src/utils/dates.ts";
import { buildHumanDecisionPayload } from "../src/utils/humanDecision.ts";

test("India port selection excludes non-Indian ports returned by an over-broad API response", () => {
  const ports = [
    { id: "in-1", name: "Paradip", unlocode: "INPRT" },
    { id: "in-2", name: "Dhamra", unlocode: "INDMQ" },
    { id: "au-1", name: "Melbourne", unlocode: "AUMEL" },
    { id: "us-1", name: "New York", unlocode: "USNYC" },
  ];

  const result = filterPortsByCountry(ports, "IN");

  assert.deepEqual(result.map(port => port.id), ["in-1", "in-2"]);
});

test("port filtering accepts country_code metadata when UN/LOCODE is unavailable", () => {
  const ports = [
    { id: "in-1", name: "India Port", country_code: "IN", unlocode: null },
    { id: "au-1", name: "Australia Port", country_code: "AU", unlocode: null },
  ];

  const result = filterPortsByCountry(ports, "in");

  assert.deepEqual(result.map(port => port.id), ["in-1"]);
});

test("date rendering preserves the selected calendar day", () => {
  assert.equal(formatDateOnly("2026-10-01T00:00:00"), "01/10/2026");
  assert.equal(formatDateOnly("2027-01-03T23:59:59"), "03/01/2027");
});

test("date rendering never produces a timezone-shifted day", () => {
  assert.equal(formatDateOnly("2026-10-01"), "01/10/2026");
});

test("invalid delivery date displays a safe placeholder", () => {
  assert.equal(formatDateOnly(""), "—");
  assert.equal(formatDateOnly("not-a-date"), "—");
});

test("MODIFY human decisions carry the explicit wait horizon", () => {
  const payload = buildHumanDecisionPayload(
    "decision-123",
    "MODIFY",
    "MODIFY from regression test.",
    { wait_days: 7 },
  );

  assert.deepEqual(payload, {
    decision_run_id: "decision-123",
    action: "MODIFY",
    modified_parameters: { wait_days: 7 },
    reason: "MODIFY from regression test.",
    actor_reference: "CHARTERPULSE_WEB_USER",
  });
});

test("APPROVE human decisions do not invent modification parameters", () => {
  const payload = buildHumanDecisionPayload(
    "decision-123",
    "APPROVE",
    "APPROVE from regression test.",
  );

  assert.deepEqual(payload.modified_parameters, {});
});
