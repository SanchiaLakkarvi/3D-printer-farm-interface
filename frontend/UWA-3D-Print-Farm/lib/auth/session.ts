/** Session token helpers — Bearer token lives in sessionStorage only. */

const ACCESS_TOKEN_KEY = "access_token";

export function getAccessToken(): string | null {
  if (typeof sessionStorage === "undefined") return null;
  return sessionStorage.getItem(ACCESS_TOKEN_KEY);
}

export function setAccessToken(token: string): void {
  sessionStorage.setItem(ACCESS_TOKEN_KEY, token);
}

export function clearAccessToken(): void {
  if (typeof sessionStorage === "undefined") return;
  sessionStorage.removeItem(ACCESS_TOKEN_KEY);
}
