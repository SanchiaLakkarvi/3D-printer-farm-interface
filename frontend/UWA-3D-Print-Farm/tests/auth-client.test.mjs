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

function installSessionStorage() {
  const store = new Map();
  globalThis.sessionStorage = {
    getItem(key) {
      return store.has(key) ? store.get(key) : null;
    },
    setItem(key, value) {
      store.set(key, String(value));
    },
    removeItem(key) {
      store.delete(key);
    },
    clear() {
      store.clear();
    },
  };
  return store;
}

beforeEach(() => {
  installSessionStorage();
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000";
});

test("signupStudent POSTs exactly the five backend fields", async () => {
  const calls = [];
  globalThis.fetch = async (url, init = {}) => {
    calls.push({ url: String(url), init });
    return new Response(
      JSON.stringify({
        id: "11111111-1111-4111-8111-111111111111",
        email: "22701234@student.uwa.edu.au",
        first_name: "Ada",
        last_name: "Lovelace",
        role: "student",
        department: "Mechanical Engineering",
        student_number: "22701234",
      }),
      { status: 201, headers: { "content-type": "application/json" } },
    );
  };

  const { signupStudent } = await vite.ssrLoadModule("/lib/auth/client.ts");
  await signupStudent({
    first_name: "Ada",
    last_name: "Lovelace",
    email: "22701234@student.uwa.edu.au",
    password: "secure-password-1",
    department: "Mechanical Engineering",
  });

  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, "http://localhost:8000/api/auth/signup");
  assert.equal(calls[0].init.method, "POST");
  assert.match(calls[0].init.headers["Content-Type"], /application\/json/i);
  assert.deepEqual(JSON.parse(calls[0].init.body), {
    first_name: "Ada",
    last_name: "Lovelace",
    email: "22701234@student.uwa.edu.au",
    password: "secure-password-1",
    department: "Mechanical Engineering",
  });
});

test("resolveDepartment maps Other free text to department", async () => {
  const { resolveDepartment } = await vite.ssrLoadModule("/lib/auth/client.ts");
  assert.equal(
    resolveDepartment("Other", "Biomedical Engineering"),
    "Biomedical Engineering",
  );
  assert.equal(
    resolveDepartment("Mechanical Engineering", "ignored"),
    "Mechanical Engineering",
  );
});

test("signupStudent success does not store an access token", async () => {
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        id: "11111111-1111-4111-8111-111111111111",
        email: "22701234@student.uwa.edu.au",
        first_name: "Ada",
        last_name: "Lovelace",
        role: "student",
        department: "IT",
        student_number: "22701234",
      }),
      { status: 201, headers: { "content-type": "application/json" } },
    );

  const { signupStudent } = await vite.ssrLoadModule("/lib/auth/client.ts");
  const { getAccessToken, setAccessToken, clearAccessToken } =
    await vite.ssrLoadModule("/lib/auth/session.ts");

  assert.equal(getAccessToken(), null);
  await signupStudent({
    first_name: "Ada",
    last_name: "Lovelace",
    email: "22701234@student.uwa.edu.au",
    password: "secure-password-1",
    department: "IT",
  });
  assert.equal(getAccessToken(), null);

  setAccessToken("stale-token");
  clearAccessToken();
  assert.equal(getAccessToken(), null);
});

test("signupStudent surfaces backend error message when present", async () => {
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        detail: {
          code: "INVALID_STUDENT_EMAIL",
          message: "Email must be a UWA student address",
        },
      }),
      { status: 400, headers: { "content-type": "application/json" } },
    );

  const { signupStudent, AuthApiError } = await vite.ssrLoadModule(
    "/lib/auth/client.ts",
  );

  await assert.rejects(
    () =>
      signupStudent({
        first_name: "Ada",
        last_name: "Lovelace",
        email: "ada@uwa.edu.au",
        password: "secure-password-1",
        department: "engineering",
      }),
    (error) => {
      assert.ok(error instanceof AuthApiError);
      assert.equal(error.message, "Email must be a UWA student address");
      assert.equal(error.status, 400);
      assert.equal(error.code, "INVALID_STUDENT_EMAIL");
      return true;
    },
  );
});

test("signupStudent uses generic fallback when response has no message", async () => {
  globalThis.fetch = async () =>
    new Response("{}", {
      status: 500,
      headers: { "content-type": "application/json" },
    });

  const { signupStudent, AuthApiError } = await vite.ssrLoadModule(
    "/lib/auth/client.ts",
  );

  await assert.rejects(
    () =>
      signupStudent({
        first_name: "Ada",
        last_name: "Lovelace",
        email: "22701234@student.uwa.edu.au",
        password: "secure-password-1",
        department: "engineering",
      }),
    (error) => {
      assert.ok(error instanceof AuthApiError);
      assert.equal(error.message, "Something went wrong. Please try again.");
      return true;
    },
  );
});
