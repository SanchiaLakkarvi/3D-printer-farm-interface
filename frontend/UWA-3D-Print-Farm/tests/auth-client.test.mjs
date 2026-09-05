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

const sampleProfile = {
  id: "11111111-1111-4111-8111-111111111111",
  email: "22701234@student.uwa.edu.au",
  first_name: "Ada",
  last_name: "Lovelace",
  role: "student",
  department: "Mechanical Engineering",
  student_number: "22701234",
};

test("signIn POSTs email and password only", async () => {
  const calls = [];
  globalThis.fetch = async (url, init = {}) => {
    calls.push({ url: String(url), init });
    return new Response(
      JSON.stringify({
        access_token: "tok-abc",
        token_type: "bearer",
        user: sampleProfile,
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    );
  };

  const { signIn } = await vite.ssrLoadModule("/lib/auth/client.ts");
  const result = await signIn("22701234@student.uwa.edu.au", "secure-password-1");

  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, "http://localhost:8000/api/auth/signin");
  assert.equal(calls[0].init.method, "POST");
  assert.deepEqual(JSON.parse(calls[0].init.body), {
    email: "22701234@student.uwa.edu.au",
    password: "secure-password-1",
  });
  assert.equal(result.access_token, "tok-abc");
  assert.equal(result.user.role, "student");
});

test("signInWithRoleMatch stores token when profile Role matches", async () => {
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        access_token: "tok-match",
        token_type: "bearer",
        user: sampleProfile,
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    );

  const { signInWithRoleMatch } = await vite.ssrLoadModule("/lib/auth/client.ts");
  const { getAccessToken } = await vite.ssrLoadModule("/lib/auth/session.ts");

  const user = await signInWithRoleMatch(
    "22701234@student.uwa.edu.au",
    "secure-password-1",
    "student",
  );

  assert.equal(user.role, "student");
  assert.equal(getAccessToken(), "tok-match");
});

test("signInWithRoleMatch discards token on Role mismatch", async () => {
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        access_token: "tok-mismatch",
        token_type: "bearer",
        user: sampleProfile,
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    );

  const { signInWithRoleMatch, AuthApiError, ROLE_MISMATCH_ERROR } =
    await vite.ssrLoadModule("/lib/auth/client.ts");
  const { getAccessToken, setAccessToken } = await vite.ssrLoadModule(
    "/lib/auth/session.ts",
  );

  setAccessToken("pre-existing");

  await assert.rejects(
    () =>
      signInWithRoleMatch(
        "22701234@student.uwa.edu.au",
        "secure-password-1",
        "farmer",
      ),
    (error) => {
      assert.ok(error instanceof AuthApiError);
      assert.equal(error.message, ROLE_MISMATCH_ERROR);
      assert.equal(error.code, "ROLE_MISMATCH");
      return true;
    },
  );

  assert.equal(getAccessToken(), null);
});

test("signIn surfaces backend error message when present", async () => {
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        detail: {
          code: "INVALID_CREDENTIALS",
          message: "Email or password is incorrect",
        },
      }),
      { status: 401, headers: { "content-type": "application/json" } },
    );

  const { signIn, AuthApiError } = await vite.ssrLoadModule("/lib/auth/client.ts");

  await assert.rejects(
    () => signIn("ada@student.uwa.edu.au", "wrong"),
    (error) => {
      assert.ok(error instanceof AuthApiError);
      assert.equal(error.message, "Email or password is incorrect");
      assert.equal(error.status, 401);
      return true;
    },
  );
});

test("fetchMe sends Authorization Bearer and returns profile", async () => {
  const calls = [];
  globalThis.fetch = async (url, init = {}) => {
    calls.push({ url: String(url), init });
    return new Response(JSON.stringify(sampleProfile), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  };

  const { fetchMe } = await vite.ssrLoadModule("/lib/auth/client.ts");
  const { setAccessToken } = await vite.ssrLoadModule("/lib/auth/session.ts");
  setAccessToken("tok-restore");

  const user = await fetchMe();
  assert.equal(user.email, sampleProfile.email);
  assert.equal(calls[0].url, "http://localhost:8000/api/auth/me");
  assert.equal(calls[0].init.method, "GET");
  assert.equal(calls[0].init.headers.Authorization, "Bearer tok-restore");
});

test("restoreSession returns profile on valid token and skips Role-match", async () => {
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ ...sampleProfile, role: "admin" }), {
      status: 200,
      headers: { "content-type": "application/json" },
    });

  const { restoreSession } = await vite.ssrLoadModule("/lib/auth/client.ts");
  const { setAccessToken, getAccessToken } = await vite.ssrLoadModule(
    "/lib/auth/session.ts",
  );
  setAccessToken("tok-valid");

  const user = await restoreSession();
  assert.equal(user?.role, "admin");
  assert.equal(getAccessToken(), "tok-valid");
});

test("restoreSession clears storage when token is invalid", async () => {
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        detail: { code: "UNAUTHORIZED", message: "Invalid token" },
      }),
      { status: 401, headers: { "content-type": "application/json" } },
    );

  const { restoreSession } = await vite.ssrLoadModule("/lib/auth/client.ts");
  const { setAccessToken, getAccessToken } = await vite.ssrLoadModule(
    "/lib/auth/session.ts",
  );
  setAccessToken("tok-expired");

  const user = await restoreSession();
  assert.equal(user, null);
  assert.equal(getAccessToken(), null);
});

test("signOut clears token and best-effort POSTs signout", async () => {
  const calls = [];
  globalThis.fetch = async (url, init = {}) => {
    calls.push({ url: String(url), init });
    return new Response(null, { status: 204 });
  };

  const { signOut } = await vite.ssrLoadModule("/lib/auth/client.ts");
  const { setAccessToken, getAccessToken } = await vite.ssrLoadModule(
    "/lib/auth/session.ts",
  );
  setAccessToken("tok-logout");

  await signOut();
  assert.equal(getAccessToken(), null);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, "http://localhost:8000/api/auth/signout");
  assert.equal(calls[0].init.method, "POST");
  assert.equal(calls[0].init.headers.Authorization, "Bearer tok-logout");
});

test("signOut still clears token when Sign-out request fails", async () => {
  globalThis.fetch = async () => {
    throw new Error("network down");
  };

  const { signOut } = await vite.ssrLoadModule("/lib/auth/client.ts");
  const { setAccessToken, getAccessToken } = await vite.ssrLoadModule(
    "/lib/auth/session.ts",
  );
  setAccessToken("tok-logout");

  await signOut();
  assert.equal(getAccessToken(), null);
});
