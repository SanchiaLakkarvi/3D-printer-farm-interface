/**
 * Email confirmation URL helpers.
 *
 * Prefer token_hash + explicit Confirm button (POST) so Outlook/Safe Links GET
 * prefetch cannot auto-confirm. Do not treat confirmation tokens as an app session.
 */

export const EMAIL_CONFIRMED_MESSAGE =
  "Your email is verified. Sign in with your password.";

const PENDING_SIGNUP_EMAIL_KEY = "uwa_pending_signup_email";

export type EmailConfirmationResult = {
  /** Legacy / post-confirm redirect flag — already confirmed. */
  confirmed: boolean;
  /** Present when the email linked here with token_hash; needs a button click. */
  pendingTokenHash: string | null;
  pendingType: string;
  error: string | null;
};

/** Remember the address shown on the post-signup verify screen (session only). */
export function rememberPendingSignupEmail(email: string): void {
  try {
    sessionStorage.setItem(PENDING_SIGNUP_EMAIL_KEY, email.trim());
  } catch {
    // sessionStorage may be unavailable (private mode / SSR); ignore.
  }
}

/** Read and clear the pending signup email after confirmation (or when leaving). */
export function takePendingSignupEmail(): string | null {
  try {
    const value = sessionStorage.getItem(PENDING_SIGNUP_EMAIL_KEY);
    if (value) sessionStorage.removeItem(PENDING_SIGNUP_EMAIL_KEY);
    return value;
  } catch {
    return null;
  }
}

function paramsFrom(searchOrHash: string): URLSearchParams {
  const raw =
    searchOrHash.startsWith("?") || searchOrHash.startsWith("#")
      ? searchOrHash.slice(1)
      : searchOrHash;
  return new URLSearchParams(raw);
}

function isConfirmType(type: string | null): boolean {
  return type === "signup" || type === "email";
}

/**
 * Read confirmation markers from the current URL (query + hash).
 * Does not mutate location — call `clearConfirmationParamsFromUrl` after handling.
 */
export function readEmailConfirmationRedirect(
  search: string,
  hash: string,
): EmailConfirmationResult {
  const query = paramsFrom(search);
  const fragment = paramsFrom(hash);

  const errorDescription =
    query.get("error_description") ??
    fragment.get("error_description") ??
    query.get("error") ??
    fragment.get("error");

  if (errorDescription) {
    return {
      confirmed: false,
      pendingTokenHash: null,
      pendingType: "signup",
      error: errorDescription.replace(/\+/g, " "),
    };
  }

  const tokenHash =
    query.get("token_hash") ?? fragment.get("token_hash") ?? null;
  const type = query.get("type") ?? fragment.get("type") ?? "signup";

  // token_hash means "show Confirm button" — never auto-confirm on page load.
  if (tokenHash && isConfirmType(type)) {
    return {
      confirmed: false,
      pendingTokenHash: tokenHash,
      pendingType: type,
      error: null,
    };
  }

  const flagged = query.get("email_confirmed") === "1";
  // Legacy: provider already confirmed and redirected with a flag / access_token.
  const confirmed =
    flagged ||
    (Boolean(fragment.get("access_token")) && isConfirmType(type));

  return {
    confirmed,
    pendingTokenHash: null,
    pendingType: type,
    error: null,
  };
}

/** Strip confirmation query/hash so a refresh does not re-trigger the banner. */
export function clearConfirmationParamsFromUrl(
  replaceState: (url: string) => void = (url) => {
    window.history.replaceState({}, "", url);
  },
  pathname: string = typeof window !== "undefined"
    ? window.location.pathname
    : "/",
): void {
  replaceState(pathname);
}

/**
 * Consume confirmation markers: read, then clear the URL when anything was present.
 * Keeps token_hash in the returned result so the Confirm button can still POST it.
 */
export function consumeEmailConfirmationRedirect(
  search: string,
  hash: string,
  replaceState?: (url: string) => void,
  pathname?: string,
): EmailConfirmationResult {
  const result = readEmailConfirmationRedirect(search, hash);
  const query = paramsFrom(search);
  const fragment = paramsFrom(hash);
  const hadParams =
    result.confirmed ||
    result.pendingTokenHash !== null ||
    result.error !== null ||
    query.has("email_confirmed") ||
    query.has("token_hash") ||
    query.has("type") ||
    fragment.has("access_token") ||
    fragment.has("token_hash") ||
    fragment.has("type") ||
    query.has("error") ||
    fragment.has("error") ||
    query.has("error_description") ||
    fragment.has("error_description");

  if (hadParams) {
    clearConfirmationParamsFromUrl(replaceState, pathname);
  }
  return result;
}
