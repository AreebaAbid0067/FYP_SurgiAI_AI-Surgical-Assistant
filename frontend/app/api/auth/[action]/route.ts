import { NextRequest, NextResponse } from "next/server";
import { BACKEND_URL, TOKEN_COOKIE } from "../../../lib/config";

export async function POST(
  request: NextRequest,
  { params }: { params: { action: string } }
): Promise<Response> {
  const { action } = params;

  if (action === "logout") {
    const response = NextResponse.json({ ok: true });
    response.cookies.delete(TOKEN_COOKIE);
    return response;
  }
  if (action !== "login" && action !== "register") {
    return NextResponse.json({ detail: "Not found." }, { status: 404 });
  }

  let backendResponse: Response;
  try {
    backendResponse = await fetch(`${BACKEND_URL}/auth/${action}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: await request.text(),
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      { detail: "Could not reach the SurgiAI service. Please try again shortly." },
      { status: 502 }
    );
  }

  const body = await backendResponse.json().catch(() => ({}));
  if (!backendResponse.ok) {
    const detail =
      typeof body.detail === "string"
        ? body.detail
        : "Please check the details you entered.";
    return NextResponse.json({ detail }, { status: backendResponse.status });
  }

  const response = NextResponse.json({ user: body.user });
  response.cookies.set(TOKEN_COOKIE, body.token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 8 * 60 * 60,
  });
  return response;
}
