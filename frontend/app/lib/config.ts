export const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
export const TOKEN_COOKIE = "surgiai_token";

export type Role = "surgeon" | "admin";

export type SessionUser = {
  user_id: number;
  username: string;
  full_name: string;
  role: Role;
};
