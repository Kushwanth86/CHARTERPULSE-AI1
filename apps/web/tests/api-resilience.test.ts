import test from "node:test";
import assert from "node:assert/strict";

test("request retries transient 502 responses and succeeds", async () => {
  const originalFetch = globalThis.fetch;
  let calls = 0;

  globalThis.fetch = (async () => {
    calls += 1;
    if (calls < 3) {
      return new Response("bad gateway", { status: 502 });
    }
    return new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  }) as typeof fetch;

  try {
    const { request } = await import("../src/api.ts");
    const result = await request<{ ok: boolean }>("/health");
    assert.deepEqual(result, { ok: true });
    assert.equal(calls, 3);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("freight forecast falls back to the explicit reference when the API is unavailable", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (async () => {
    throw new Error("network unavailable");
  }) as typeof fetch;

  try {
    const { listFreightForecasts } = await import("../src/api.ts");
    const result = await listFreightForecasts("origin", "destination");
    assert.equal(result.length, 1);
    assert.equal(result[0].provenance, "PUBLIC_PROXY");
  } finally {
    globalThis.fetch = originalFetch;
  }
});
