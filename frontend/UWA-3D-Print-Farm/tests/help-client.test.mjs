import assert from "node:assert/strict";
import test, { after, beforeEach } from "node:test";
import { fileURLToPath } from "node:url";
import { createServer } from "vite";

const root = fileURLToPath(new URL("..", import.meta.url));
const vite = await createServer({
  appType: "custom",
  configFile: false,
  root,
  resolve: { alias: { "@": root } },
  server: { middlewareMode: true },
});

after(async () => {
  await vite.close();
});

beforeEach(() => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000";
});

test("sendHelpMessage posts the current message and history window", async () => {
  const calls = [];
  globalThis.fetch = async (url, init = {}) => {
    calls.push({ url: String(url), init });
    return new Response(JSON.stringify({ message: "Use the six-digit code." }), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  };

  const { sendHelpMessage } = await vite.ssrLoadModule("/lib/help/client.ts");
  const result = await sendHelpMessage("How do I verify?", [
    { role: "user", content: "I signed up." },
    { role: "assistant", content: "Check your email." },
  ]);

  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, "http://localhost:8000/api/help/chat");
  assert.equal(calls[0].init.method, "POST");
  assert.deepEqual(JSON.parse(calls[0].init.body), {
    message: "How do I verify?",
    history: [
      { role: "user", content: "I signed up." },
      { role: "assistant", content: "Check your email." },
    ],
  });
  assert.equal(result.message, "Use the six-digit code.");
});

test("sendHelpMessage surfaces the structured unavailable message", async () => {
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        detail: {
          code: "HELP_UNAVAILABLE",
          message: "Help chat is temporarily unavailable. Please try again later.",
        },
      }),
      { status: 503, headers: { "content-type": "application/json" } },
    );

  const { sendHelpMessage, HelpApiError } = await vite.ssrLoadModule(
    "/lib/help/client.ts",
  );

  await assert.rejects(
    () => sendHelpMessage("Can you help?"),
    (error) => {
      assert.ok(error instanceof HelpApiError);
      assert.equal(error.status, 503);
      assert.equal(error.code, "HELP_UNAVAILABLE");
      assert.match(error.message, /temporarily unavailable/i);
      return true;
    },
  );
});

test("sendHelpMessage uses a stable error when fetch fails", async () => {
  globalThis.fetch = async () => {
    throw new Error("network detail that must not be shown");
  };
  const { sendHelpMessage, HelpApiError } = await vite.ssrLoadModule(
    "/lib/help/client.ts",
  );

  await assert.rejects(
    () => sendHelpMessage("Can you help?"),
    (error) => {
      assert.ok(error instanceof HelpApiError);
      assert.equal(error.status, 0);
      assert.equal(
        error.message,
        "Help chat is unavailable. Please try again later.",
      );
      return true;
    },
  );
});
