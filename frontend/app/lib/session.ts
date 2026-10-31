import { cookies } from "next/headers";
import { BACKEND_URL, SessionUser, TOKEN_COOKIE } from "./config";

export async function getSession(): Promise<SessionUser | null> {
  const token = cookies().get(TOKEN_COOKIE)?.value;
  if (!token) return null;
  try {
    const response = await fetch(`${BACKEND_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    return response.ok ? ((await response.json()) as SessionUser) : null;
  } catch {
    return null;
  }
}
