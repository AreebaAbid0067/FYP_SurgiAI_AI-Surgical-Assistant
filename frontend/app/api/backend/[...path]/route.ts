import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { BACKEND_URL, TOKEN_COOKIE } from "../../../lib/config";

export const dynamic = "force-dynamic";

// Authenticated pass-through to the FastAPI backend. The session token lives
// in an HttpOnly cookie, so browser scripts never see it.
async function forward(
  request: NextRequest,
  { params }: { params: { path: string[] } }
): Promise<Response> {
  if (params.path[0] === "auth") {
    return NextResponse.json({ detail: "Not found." }, { status: 404 });
  }
  const token = cookies().get(TOKEN_COOKIE)?.value;
  if (!token) {
    return NextResponse.json({ detail: "Authentication required." }, { status: 401 });
  }

  const headers: Record<string, string> = { Authorization: `Bearer ${token}` };
  const contentType = request.headers.get("content-type");
  if (contentType) headers["Content-Type"] = contentType;
  const hasBody = request.method !== "GET" && request.method !== "DELETE";

  try {
    const response = await fetch(
      `${BACKEND_URL}/${params.path.join("/")}${request.nextUrl.search}`,
      {
        method: request.method,
        headers,
        body: hasBody ? await request.arrayBuffer() : undefined,
        cache: "no-store",
      }
    );
    const responseHeaders = new Headers();
    for (const name of ["content-type", "content-disposition"]) {
      const value = response.headers.get(name);
      if (value) responseHeaders.set(name, value);
    }
    return new Response(await response.arrayBuffer(), {
      status: response.status,
      headers: responseHeaders,
    });
  } catch {
    return NextResponse.json(
      { detail: "The SurgiAI service is unreachable. Clinical assistance is currently unavailable." },
      { status: 502 }
    );
  }
}

export { forward as GET, forward as POST, forward as PUT, forward as DELETE };
