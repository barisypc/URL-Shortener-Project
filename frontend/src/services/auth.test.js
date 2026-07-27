// frontend/src/services/auth.test.js
import { getToken, logout, isTokenExpired, isAuthenticated } from "./auth";

// tiny helper to build a fake JWT with a given expiry, without hitting the backend
function fakeToken(expSecondsFromNow) {
  const payload = { exp: Math.floor(Date.now() / 1000) + expSecondsFromNow };
  const b64 = (obj) => btoa(JSON.stringify(obj));
  return `${b64({ alg: "none" })}.${b64(payload)}.signature`;
}

beforeEach(() => {
  localStorage.clear();
});

test("getToken returns null when nothing stored", () => {
  expect(getToken()).toBeNull();
});

test("isTokenExpired returns true when no token exists", () => {
  expect(isTokenExpired()).toBe(true);
});

test("isTokenExpired returns false for a token that expires in the future", () => {
  localStorage.setItem("token", fakeToken(3600)); // expires in 1 hour
  expect(isTokenExpired()).toBe(false);
});

test("isTokenExpired returns true for an already-expired token", () => {
  localStorage.setItem("token", fakeToken(-3600)); // expired 1 hour ago
  expect(isTokenExpired()).toBe(true);
});

test("isAuthenticated logs out and returns false when token is expired", () => {
  localStorage.setItem("token", fakeToken(-100));
  expect(isAuthenticated()).toBe(false);
  expect(getToken()).toBeNull(); // logout() should have cleared it
});





// frontend/src/services/auth.test.js (continued)
import { login } from "./auth";

beforeEach(() => {
  localStorage.clear();
  global.fetch = jest.fn();
});

test("login stores the access token on success", async () => {
  global.fetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ access_token: "abc123" }),
  });

  await login("user@example.com", "Aa1.gucluSifre");

  expect(getToken()).toBe("abc123");
});

test("login throws with backend's error message on failure", async () => {
  global.fetch.mockResolvedValueOnce({
    ok: false,
    json: async () => ({ detail: "Incorrect email or password" }),
  });

  await expect(login("user@example.com", "wrong")).rejects.toThrow(
    "Incorrect email or password"
  );
});

test("login rejects immediately if email or password is missing", async () => {
  await expect(login("", "somepassword")).rejects.toThrow();
  expect(global.fetch).not.toHaveBeenCalled(); // shouldn't even attempt the request
});