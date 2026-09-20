import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { listPorts, recordHumanDecision } from "../src/api.ts";

const appSource = readFileSync(
  new URL("../src/App.tsx", import.meta.url),
  "utf8",
);

test("India port selection filters an over-broad primary API response", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () =>
    ({
      ok: true,
      json: async () => ({
        count: 4,
        data: [
          { id: "in-1", name: "Paradip", unlocode: "INPRT" },
          { id: "in-2", name: "Dhamra", unlocode: "INDMQ" },
          { id: "au-1", name: "Melbourne", unlocode: "AUMEL" },
          { id: "us-1", name: "New York", unlocode: "USNYC" },
        ],
      }),
      text: async () => "",
    }) as Response;

  try {
    const result = await listPorts("IN");
    assert.deepEqual(result.map(port => port.id), ["in-1", "in-2"]);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("MODIFY human decisions preserve the explicit wait horizon in the request body", async () => {
  const originalFetch = globalThis.fetch;
  const requests: RequestInit[] = [];
  globalThis.fetch = async (_input, init) => {
    requests.push(init || {});
    return {
      ok: true,
      json: async () => ({
        id: "human-1",
        decision_run_id: "decision-123",
        action: "MODIFY",
        modified_parameters: { wait_days: 7 },
        reason: "MODIFY from regression test.",
        decided_at: "2026-09-20T00:00:00Z",
        actor_reference: "CHARTERPULSE_WEB_USER",
        provenance: "USER_PROVIDED",
      }),
      text: async () => "",
    } as Response;
  };

  try {
    await (recordHumanDecision as unknown as (
      decisionRunId: string,
      action: "APPROVE" | "MODIFY" | "REJECT",
      reason: string,
      modifiedParameters: Record<string, unknown>,
    ) => Promise<unknown>)(
      "decision-123",
      "MODIFY",
      "MODIFY from regression test.",
      { wait_days: 7 },
    );

    const body = JSON.parse(String(requests[0]?.body || "{}"));
    assert.deepEqual(body.modified_parameters, { wait_days: 7 });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("Decision Room delivery dates are rendered through date-only formatting", () => {
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

