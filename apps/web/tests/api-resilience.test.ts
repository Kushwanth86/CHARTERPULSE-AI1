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

test("freight forecast surfaces a persistent API failure instead of masking it as no data", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (async () =>
    new Response("bad gateway", { status: 502 })) as typeof fetch;

  try {
    const { listFreightForecasts } = await import("../src/api.ts");
    await assert.rejects(
      () => listFreightForecasts("origin", "destination"),
      /API 502: bad gateway/,
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("request does not retry non-idempotent POST operations", async () => {
  const originalFetch = globalThis.fetch;
  let calls = 0;

  globalThis.fetch = (async () => {
    calls += 1;
    return new Response("bad gateway", { status: 502 });
  }) as typeof fetch;

  try {
    const { request } = await import("../src/api.ts");
    await assert.rejects(
      () => request("/api/v1/cargo", { method: "POST", body: "{}" }),
      /API 502: bad gateway/,
    );
    assert.equal(calls, 1);
  } finally {
    globalThis.fetch = originalFetch;
  }
});



test("formatApiError explains missing Freightos quotes without exposing raw API JSON", async () => {
  const { formatApiError } = await import("../src/api.ts");
  const message = formatApiError(
    new Error('API 404: {"detail":"No freight quotes are available for this route and container type."}'),
    "Fallback",
  );

  assert.match(message, /No freight quotes are available/);
  assert.match(message, /Try another port pair or container type/);
  assert.match(message, /No rate has been assumed/);
  assert.doesNotMatch(message, /API 404|\\"detail\\"/);
});
